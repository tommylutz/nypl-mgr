#!python
import requests
import logging
from pprint import pformat
import sys
import argparse
import re
from xml.sax.saxutils import unescape
from nypl import NYPL,NYPL_CrawlingError
#Stuff I had to do to get this to work:
# $ git clone git://github.com/kennethreitz/requests.git
# $ cd requests
# $ python setup.py install
#
# $ pip install certifi
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
            '-s','--showbooks',
            dest='showbooks',
            action='store_const',
            const=True, default=False,
            help='List all books checked out')

        parser.add_argument(
            '-r','--renewbook',
            type=str,
            metavar='BOOK_TITLE',
            nargs='+',
            dest='renewbooks',
            default='',
            help='Title of the book(s) you wish to renew (substring, case-insensitive match). Can specify multiple times.')
            
            
        
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
    
    def showbooks(self):
        return self._args.showbooks
    
    def renewbooks(self):
        return self._args.renewbooks
    
    def __del__(self):
        pass
        
       
def main():
    global gConfig
    gConfig = Config()
       
    if (not gConfig.barcode() or not gConfig.pin()):
        logging.error("You must supply a PIN and Library Barcode # with -p and -b, respectively")
        return 1
        
    nypl = NYPL()
    try:
        nypl.logon(barcode=gConfig.barcode(),pin=gConfig.pin())
    except NYPL_LoginError, ex:
        logging.error("Failed to login with http status [%s], errors: [%s]"%(ex.http_status(),ex.error_message()))
        logging.debug("Page text: [%s]"%(ex.page_text()))
        sys.exit(1)
    
    try:
        nypl.load_checked_out_books()
    except NYPL_CrawlingError, ex:
        logging.error("Failed to load checked out books")
        logging.debug(str(ex))
        sys.exit(1)
    
    for bookTitle in gConfig.renewbooks():
        try:
            nypl.renew_book_by_title(bookTitle)
            logging.info("Renewal submitted for book [%s]"%(bookTitle))
        except NYPL_CrawlingError, ex:
            logging.error("Failed to renew book by title: "+str(ex))    
    
    if gConfig.showbooks():
        try:
            nypl.load_checked_out_books()
            for book in nypl.books():
                logging.info("================CHECKED OUT BOOKS==================")
                logging.info(" Title: %s"%(book["Title"]))
                logging.info(" Status: %s"%(book["Status"]))
                logging.info(" Call Number: %s"%(book["Call Number"]))
                logging.info(" Barcode: %s"%(book["Barcode"]))
                logging.info("--------------------------------------------------")
        except NYPL_CrawlingError, ex:
            logging.error("Failed to load checked out books(2)")
            logging.debug(str(ex))

            

if __name__ == "__main__":
    main()