import logging
import requests
import re
from pprint import pformat,pprint
import sys
from xml.sax.saxutils import unescape
import time
from HTMLParser import HTMLParser

def dbg_response(r):
    logging.debug("Got page: %s"%(pformat(r)))
    logging.debug("Text: %s"%(r.text))
    logging.debug("Header: %s"%(r.headers))
    logging.debug("Status Code: %s"%(r.status_code))

    
class NYPL_ItemParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._books = []
        self.empty_book = { 
            "Title" : None, 
            "Status" : None, 
            "Call Number" : None,
            "Barcode" : None}
        self.current_book = dict(self.empty_book)
        self.current_attr = None
        self.current_renewal_attributes = None
        
    def books(self):
        return self._books
        
    def attrlist_to_dict(self,attrs):
        rv = dict()
        for attr in attrs:
            rv[attr[0]] = attr[1]
        return rv
     
    def print_books_to_stdout(self):
        print ""
        print "======== YOUR NYPL LIBRARY BOOKS CHECKED OUT RIGHT NOW ==========="
        for book in self._books:
            print "TITLE:   %s"%(book["Title"])
            print "STATUS:  %s"%(book["Status"])
            print "CALL #:  %s"%(book["Call Number"])
            print "BARCODE: %s"%(book["Barcode"])
            print "---------------------------------------------------------------"

    def handle_starttag(self, tag, attrs):
        #logging.debug("Encountered a start tag: %s, %s"%(pformat(tag),pformat(attrs)))
        self.current_attr = None
        if (tag == 'input'):
            #Find id, name, and value in the attrs dict
            self.current_renewal_attributes = self.attrlist_to_dict(attrs)
        elif (tag == 'span' or tag == 'td'):
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
                self.current_book['RenewalAttributes'] = self.current_renewal_attributes
                self._books.append(self.current_book)
                self.current_book = dict(self.empty_book)
                self.current_renewal_attributes = None
                logging.debug("I GOT A BOOK!!!! %s"%(pformat(self._books)))
            
    
class NYPL_CrawlingError(Exception):
    def __init__(self,resp):
        self._resp = resp
    
    def __str__(self):
        return "HTTP Status [%s] Header [%s], PageText [%s]"% \
                (self._resp.status_code,
                 self._resp.headers,
                 self._resp.text)
    
class NYPL_LoginError(Exception):
    def __init__(self,resp,errors=[]):
        self._resp = resp
        if isinstance(errors,basestring):
            self._error_message = errors
        else:
            self._error_message = " / ".join(errors)
        pass
        
    def http_status(self):
        return self._resp.status_code
    
    def error_message(self):
        return self._error_message
    
    def page_text(self):
        return self._resp.text
    
    def __str__(self):
        return "HTTP Status [%s] Message [%s]"%(self.http_status(),self._error_message)
        
class LibraryItem:
    def __init__(self):
        pass
    
    def __del__(self):
        pass

class NYPL:
    def __init__(self):
        pass
        
    def logon(self, barcode='', pin=''):
        self.session = requests.Session()
        r = self.session.get("https://catalog.nypl.org/iii/cas/login")
        regex_lt = re.compile("lt\" value=\"([^\"]+)\"")
        lt_var = regex_lt.findall(r.text)[0]
        logging.debug("lt var: %s"%(pformat(lt_var)))
        
        r = self.session.post("https://catalog.nypl.org/iii/cas/login", 
            data = {
                "lt"   : lt_var,
                "_eventId" : "submit",
                "code" : barcode,
                "pin"  : pin } )
        dbg_response(r)        
                
        if r.status_code != 200:
            raise NYPL_LoginError(r,["Bad HTTP Response"])
        
        regex_errors = re.compile("<div\\s+id=\"status\"\\s+class=\"errors\"\\s*>([^<]+)</div>")
        errors = regex_errors.findall(r.text)
        if len(errors):
            raise NYPL_LoginError(r,errors)
            
        r = self.session.get("https://browse.nypl.org/iii/encore/myaccount?lang=eng")
        regex_patronid = re.compile("/patroninfo\*eng/([0-9]+)/")
        patronids = regex_patronid.findall(r.text)
        if len(patronids) == 0:
            raise NYPL_LoginError(r,"Failed to find patron id in HTTP response")
        self._patronid = patronids[0]
        logging.debug("Patron ID: "+self._patronid)
            
        self._logged_on = True
    
    def books(self):
        return self._books
        
    def load_checked_out_books(self):
        assert(self._logged_on)
        self._books = []
        r = self.session.get("https://browse.nypl.org/iii/encore/myaccount?lang=eng")
        dbg_response(r)
        
        regex_checkouts_link = re.compile("(<a[^>]+>\\s*My Checkouts\\s*</a>)")
        links = regex_checkouts_link.findall(r.text)
        logging.debug("Links: %s"%(pformat(links)))
        
        link = "https://catalog.nypl.org/dp/patroninfo*eng/%s/items"%(self._patronid)
        

        r = self.session.get(link)
        dbg_response(r)
        
        parser = NYPL_ItemParser()
        parser.feed(r.text)
        
        self._books = parser.books()
        logging.debug("Retrieved books: "+pformat(self._books))
        #else:
        #    raise NYPL_CrawlingError(r)
        
#<a href="#"  onClick="return submitCheckout( 'requestRenewAll', 'requestRenewAll' )"><div onmousedown="this.className='pressedState';" onmouseout="this.className='';" onmouseup="this.className='';"><div class="buttonSpriteDiv"><span class="buttonSpriteSpan1"><span class="buttonSpriteSpan2">Renew All</span></span></div></div></a>
#<a href="#"  onClick="return submitCheckout( 'requestRenewSome', 'requestRenewSome' )"><div onmousedown="this.className='pressedState';" onmouseout="this.className='';" onmouseup="this.className='';"><div class="buttonSpriteDiv"><span class="buttonSpriteSpan1"><span class="buttonSpriteSpan2">Renew Marked</span></span></div></div></a>

    def renew_book(self,book):
        #r = self.session.post("https://catalog.nypl.org/dp/patroninfo*eng/%s/items"%(self._patronid), 
        #    data = {
        #        "currentsorderorder"   : "current_checkout,current_checkout",
        #        book["RenewalAttributes"]["id"] : book["RenewalAttributes"]["value"],
        #        "requestRenewSome" : "requestRenewSome"} )
        bookdata = {
                "currentsorderorder"   : "current_checkout,current_checkout",
                book["RenewalAttributes"]["id"] : book["RenewalAttributes"]["value"],
                "renewsome" : "YES"}
        logging.debug("Submitting book for renewal: %s"%(pformat(bookdata)))
        r = self.session.post("https://catalog.nypl.org/dp/patroninfo*eng/%s/items"%(self._patronid), 
            data = bookdata )                
        dbg_response(r)
        pass
#https://catalog.nypl.org/dp/patroninfo*eng/6435997/items
#currentsortorder: current_checkout,current_checkout
#renew0: i33261263
#renew1: i33582427
#requestRenewSome: requestRenewSome       

# is 6435997 my patron id? 

    def renew_book_by_title(self,title):
        books_renewed = 0
        logging.debug("Attempting to find book with title [%s] to renew"%(title))
        for book in self._books:
            logging.debug("Maybe it's [%s]"%(book["Title"]))
            if book["Title"].lower().find(title.lower()) >= 0:
                logging.debug("Attempting to renew [%s]"%(book["Title"]))
                self.renew_book(book)
                books_renewed += 1
        logging.debug("Book renewals submitted: %d"%(books_renewed))
    
    def __del__(self):
        pass

if __name__ == "__main__":
    logger = logging.getLogger()
    stdoutHandler = logging.StreamHandler(sys.stdout)
    logger.setLevel(logging.DEBUG)
    stdoutHandler.setLevel(logging.DEBUG)
    logger.addHandler(stdoutHandler)
    
    nypl = NYPL()
    
    try:
        nypl.logon(barcode='999999999999999',pin='1111')
    except NYPL_LoginError, ex:
        logging.debug("Failed to login with http status [%s], errors: [%s]"%(ex.http_status(),ex.error_message()))
        logging.debug("Page text: [%s]"%(ex.page_text()))
        #sys.exit(1)
    
    try:
        nypl.load_checked_out_books()
    except NYPL_CrawlingError, ex:
        logging.debug("Failed to load checked out books: "+str(ex))
        #sys.exit(1)
    
    try:
        nypl.renew_book_by_title("appalachian")
    except NYPL_CrawlingError, ex:
        logging.debug("Failed to renew book by title: "+str(ex))
    
