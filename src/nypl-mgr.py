#!python
import requests
import logging
from pprint import pformat
import sys
import argparse
import re
from xml.sax.saxutils import unescape
#Stuff I had to do to get this to work:
# $ git clone git://github.com/kennethreitz/requests.git
# $ cd requests
# $ python setup.py install
#
#
#
#

gConfig = None

class Config:
    def __init__(self):
        self._parse_args()
        self._start_logging()
    
    def _parse_args(self):
        parser = argparse.ArgumentParser(
            description='NYPL Command Line Interface')
        
        parser.add_argument(
            '-l','--logfile',
            type=str,
            metavar='LOGFILE',
            default='',
            dest='logfile',
            help='Path to log file (will not log to file if not provided)')
        
        parser.add_argument(
            '-v','--verbosity',
            type=str,
            metavar='VERBOSITY',
            default='INFO',
            dest='verbosity',
            help='Verbosity (info, debug, warn, or error)')
        
        parser.add_argument(
            '-b', '--barcode',
            type=str,
            metavar='CARD_BARCODE',
            dest='barcode',
            default='',
            help='Your library card number')
        
        parser.add_argument(
            '-p','--pin',
            type=str,
            metavar='PIN_CODE',
            dest='pin',
            default='',
            help='Your PIN number used to check out books')
        
        parser.add_argument(
            '-x','--xmlfile',
            type=str,
            metavar='XML_FILE',
            dest='xmlfile',
            default='',
            help='XML file of your checked out items to parse, from previous run')
        
        args = parser.parse_args()
        self._args = args
    
    def _start_logging(self):
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        stdoutlogger = logging.StreamHandler(sys.stdout)
        stdoutlogger.setLevel(
            getattr(logging,self._args.verbosity.upper(),logging.ERROR))
        root.addHandler(stdoutlogger)
        
        if self._args.logfile:
            filelogger = logging.StreamHandler(file(self._args.logfile,'w'))
            filelogger.setLevel(logging.DEBUG)
            root.addHandler(filelogger)
            logging.info("Log file is [%s]"%(self._args.logfile))
            
    def barcode(self):
        return self._args.barcode
    
    def pin(self):
        return self._args.pin
    
    def xmlfile(self):
        return self._args.xmlfile
    
    def __del__(self):
        pass
        
from HTMLParser import HTMLParser
class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.books = []
        self.empty_book = { 
            "Title" : None, 
            "Status" : None, 
            "Call Number" : None,
            "Barcode" : None}
        self.current_book = dict(self.empty_book)
        self.current_attr = None
     
    def print_books_to_stdout(self):
        print ""
        print "======== YOUR NYPL LIBRARY BOOKS CHECKED OUT RIGHT NOW ==========="
        for book in self.books:
            print "TITLE:   %s"%(book["Title"])
            print "STATUS:  %s"%(book["Status"])
            print "CALL #:  %s"%(book["Call Number"])
            print "BARCODE: %s"%(book["Barcode"])
            print "---------------------------------------------------------------"

    def handle_starttag(self, tag, attrs):
        #logging.debug("Encountered a start tag: %s, %s"%(pformat(tag),pformat(attrs)))
        self.current_attr = None
        if (tag == 'span' or tag == 'td'):
            if ('class','patFuncTitleMain') in attrs:
                logging.debug("!!!!!!!!!!!!!!!Found title span!!")
                self.current_attr = 'Title'
            elif ('class','patFuncStatus') in attrs:
                logging.debug("!!!!!!!!!!!!!!!Found status span!!")
                self.current_attr = 'Status'
            elif ('class','patFuncCallNo') in attrs:
                logging.debug("!!!!!!!!!!!!Found call number span!!")
                self.current_attr = 'Call Number'
            elif ('class','patFuncBarcode') in attrs:
                logging.debug("!!!!!!!!!!!!Found call number span!!")
                self.current_attr = 'Barcode'
            else:
                pass
        
    def handle_endtag(self, tag):
        #logging.debug("Encountered an end tag :%s"%(pformat(tag)))
        pass
        
    def handle_data(self, data):
        logging.debug("Encountered some data %s"%(pformat(data)))
        if self.current_attr:
            logging.debug("Setting data for attribute [%s] to [%s]"%(self.current_attr,data))
            self.current_book[self.current_attr] = data.strip()
            self.current_attr = None
            if (self.current_book['Title'] != None and
               self.current_book['Status'] != None and
               self.current_book['Call Number'] != None and
               self.current_book['Barcode'] != None):
                self.books.append(self.current_book)
                self.current_book = dict(self.empty_book)
                logging.debug("I GOT A BOOK!!!! %s"%(pformat(self.books)))
            
        
def parse_checkedout_books(html):
    parser = MyHTMLParser()
    parser.feed(html)
    parser.print_books_to_stdout()
        
def main():
    global gConfig
    gConfig = Config()
    
    if gConfig.xmlfile():
        with open(gConfig.xmlfile(),"r") as xmlfile:
            data = xmlfile.read()
            parse_checkedout_books(data)
        return 0
    
    if (not gConfig.barcode() or not gConfig.pin()):
        logging.error("You must supply a PIN and Library Barcode # with -p and -b, respectively")
        return 1
    
    with requests.Session() as s:
        r = s.get("https://catalog.nypl.org/iii/cas/login")
        regex_lt = re.compile("lt\" value=\"([^\"]+)\"")
        lt_var = regex_lt.findall(r.text)[0]
        logging.debug("lt var: %s"%(pformat(lt_var)))
        
        r = s.post("https://catalog.nypl.org/iii/cas/login", 
            data = {
                "lt"   : lt_var,
                "_eventId" : "submit",
                "code" : gConfig.barcode(),
                "pin"  : gConfig.pin() } )
        
        logging.debug("Got page: %s"%(pformat(r)))
        logging.debug("Text: %s"%(r.text))
        logging.debug("Header: %s"%(r.headers))
        logging.debug("Status Code: %s"%(r.status_code))
    
        r = s.get("https://browse.nypl.org/iii/encore/myaccount?lang=eng")
        logging.debug("Got page: %s"%(pformat(r)))
        logging.debug("Text: %s"%(r.text))
        logging.debug("Header: %s"%(r.headers))
        logging.debug("Status Code: %s"%(r.status_code))
        
        regex_checkouts_link = re.compile("(<a[^>]+>\\s*My Checkouts\\s*</a>)")
        links = regex_checkouts_link.findall(r.text)
        logging.debug("Links: %s"%(pformat(links)))
        
        if len(links) > 0:
            regex_link = re.compile("href=\"([^\"]+)\"")
            link = regex_link.findall(links[0])[0]
            link = unescape(link)
            logging.debug("Found link: %s"%(link))
            r = s.get("https://browse.nypl.org"+link+"&beventname=onClick&beventtarget.id=webpacFuncDirectLinkComponent&dojo.preventCache=1451698618237",
                    headers={
                        'dojo-ajax-request' : 'true',
                        'Referer' : 'https://browse.nypl.org/iii/encore/myaccount?lang=eng'
                        } )
            logging.debug("Got page: %s"%(pformat(r)))
            logging.debug("Text: %s"%(r.text))
            logging.debug("Header: %s"%(r.headers))
            logging.debug("Status Code: %s"%(r.status_code))
            
            regex_link = re.compile("src=\"(https://catalog.nypl.org.*items)\"")
            link = regex_link.findall(r.text)[0]
            link = unescape(link)
            logging.debug("Found items link!! %s"%(link))

            r = s.get(link)
            logging.debug("Got page: %s"%(pformat(r)))
            logging.debug("Text: %s"%(r.text))
            logging.debug("Header: %s"%(r.headers))
            logging.debug("Status Code: %s"%(r.status_code))
            #ofile = file("books.xml","w")
            #ofile.write(r.text)
            #logging.debug("Wrote to file books.xml")
            
            parse_checkedout_books(r.text)
            

if __name__ == "__main__":
    main()