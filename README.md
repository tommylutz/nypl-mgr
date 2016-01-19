## NYPL Book Manager

This experimental application, in its infancy, lists your checked out books along with their due dates
It can be run from the command line:
```
nypl-mgr.py -b <LIBRARY BARCODE> -p <PIN> [--showbooks] [--renewbook "BookTitle1" "BookTitle2" ... "BootTitleN"]
```
Book renewals are searched by title, case insensitive. You must list your books after renewing to confirm the renewal request was submitted properly.


Use at your own risk. This is not a robust application and is in no way shape or 
form endorsed by or associated with the New York Public Library.
