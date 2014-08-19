#!/usr/bin/env python

import sys, urllib, urllib2, getpass, cookielib, time, fnmatch, re, os
import xml.etree.ElementTree as ET
from optparse import OptionParser
from HTMLParser import HTMLParser

usage = 'python %prog -t https://127.0.0.1:8834 -r both\n\nFollow prompts.  Report name search string can be any part of the reports name that you want to download (case insensitive). Leave it blank to display all reports on scanner.\nReport files will be downloaded to the current directory with .nessus\\nbe appended to the report name.  Be aware that it takes awhile to generate large nbe reports, the script will wait for nessus to generate a .nbe then download, but it can take a bit of time.'

parser = OptionParser(usage=usage)
parser.add_option("-t", "--target",
	 help="set the target URL protocol, host and port. Example https://127.0.0.1:8834")
parser.add_option("-r", "--report", 
         help="choose the type of report output.  Available types are 'nessus', 'nbe' or 'both' to save both types.  Omit quotes when passing as an argument.")
parser.add_option("-f", "--force", action="store_true", dest="force", default=False,
 help="Force overwriting report files that already exist (same name) in the current directory.  Passing the -f switch will overwrite existing files, while omiting will skip the file that exists and download only new reports (default behavior).")
(options, args) = parser.parse_args()
if len(sys.argv) < 4:
        parser.print_help()
        sys.exit( 1 );

class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.content = None
	self.status = None
	self.flag = 0
    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            for key, value in attrs:
                if key == 'content':
		    self.content = value[6:]
		    self.status = value[:1]
# ended up not needing text from between <title> tags, but left here for posterity
#	if tag == 'title':
#	    self.flag += 1
#
#    def handle_endtag(self,tag):
#	if tag == 'title':
#	    self.flag -= 1
#	
#    def handle_data(self,data):
#	if self.flag:
#	    self.status = data
	    

def get_content_meta(url):
    html_parser = MyHTMLParser()
    html_parser.feed(url.read())
    html_parser.close()
    return html_parser.content

def get_status(url):
    html_parser = MyHTMLParser()
    html_parser.feed(url.read())
    html_parser.close()
    return html_parser.status

def xml_parse(xml_root):
    root = ET.fromstring(xml_root)
    xml_elems = []
    for report in root.findall(".//report"):
        xml_out=report.find('name').text + ',' + report.find('readableName').text + "," + report.find('status').text
        xml_split=xml_out.split(',')
        if xml_split[2] == "completed":
            if fnmatch.fnmatch(xml_split[1].lower(), srch_str.lower()):
#                xml_split=xml_out.split(',')
                xml_elems.append((xml_split[0],xml_split[1]))
    return xml_elems

def nessus_downloader(rprt_num,rprt_name):
    rprt_name = re.sub('[^\w]', '_', rprt_name)
#    if not options.force:
    if not os.path.exists(rprt_name + ".nessus") or options.force == True:
        print '\nProcessing Nessus Scan: ' + xml_list[x][1] + '.nessus. Please wait...'
        report_dl = opener.open(nessus_server + '/file/report/download?report=' + rprt_num)
        f = open(rprt_name + '.nessus', 'w')
        f.write(report_dl.read())
        f.close()
        print '\n*** Nessus Scan: ' + xml_list[x][1] + '.nessus processing complete ***'
    else:
        print '\nNot set to force overwrite (no -f detected), skipping ' + rprt_name + '.nessus'

def nbe_downloader(rprt_num,rprt_name):
    rprt_name = re.sub('[^\w]', '_', rprt_name)
    if not os.path.exists(rprt_name + ".nbe") or options.force == True:
        print '\nProcessing Nessus Scan: ' + xml_list[x][1] + ".nbe. nbe's can take a long time if they're big, please wait..."
        nbe_opener = opener.open(nessus_server + '/file/xslt/?report=' + rprt_num + '&xslt=nbe.xsl')
        nbe_step1_url = get_content_meta(nbe_opener)
        nbe_step1_opener = opener.open(nessus_server + nbe_step1_url)
        time.sleep(1)
        while True:
            nbe_step1b_opener = opener.open(nessus_server + nbe_step1_url)
            nbe_step1b_status = get_status(nbe_step1b_opener)
            time.sleep(3)
            if nbe_step1b_status == '0':
                break
        nbe_step2_opener = opener.open(nessus_server + nbe_step1_url + '&step=2')
        f = open(rprt_name + '.nbe', 'w')
        f.write(nbe_step2_opener.read())
        f.close()
        print '\n*** Nessus Scan: ' + xml_list[x][1] + '.nbe processing complete ***'
    else:
        print '\nNot set to force overwrite (no -f detected), skipping ' + rprt_name + '.nbe'

xml_list = []

nessus_server = options.target

# Remove trailing / if they supplied one
if nessus_server[len(nessus_server)-1] == "/":
    nessus_server = nessus_server[:-1]

username=raw_input('Enter Nessus Username: ')

pdub = getpass.getpass()

srch_str= '*' + raw_input('\nEnter report name search string. You can use Unix-like wildcards (e.g. * and ?) in the search string. \nLeave blank to display all available reports: ') + '*'
print '\n'
cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
login_data = urllib.urlencode({'login' : username, 'password' : pdub})
opener.open(nessus_server + '/login', login_data)
del pdub
report_list = opener.open(nessus_server + '/report/list')
report_list_xml = report_list.read()

xml_list.extend(xml_parse(report_list_xml))
for x in range(len(xml_list)):
    print 'Nessus Scan: ' + xml_list[x][1]

raw_input('\nThe above report(s) matched your search criteria.  Press Enter to continue\nand download them to you current working directory or CTRL+C to abort')

for x in range(len(xml_list)):
    if options.report == 'both':
        nbe_downloader(xml_list[x][0],xml_list[x][1])
	nessus_downloader(xml_list[x][0],xml_list[x][1])
    elif options.report == 'nbe':
	nbe_downloader(xml_list[x][0],xml_list[x][1])
    elif options.report == 'nessus':
	nessus_downloader(xml_list[x][0],xml_list[x][1])

print '\nNessus file downloads 100% complete'
