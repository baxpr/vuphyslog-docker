#!/usr/local/bin/python

import os
import re
import datetime
import argparse
import json
import physlog_query

# Specify and parse command line arguments
parser = argparse.ArgumentParser('Package a physlog file and upload to PACS')
parser.add_argument('--pacs',required=True,
                    help='PACS as AETITLE@nnn.nnn.nnn.nnn:PORT')
parser.add_argument('--stations_file',required=True,
                    help='JSON format file with scanner station IDs')
parser.add_argument('--physlog_file',required=True,
                    help='Physlog file to upload')
parser.add_argument('--physlog_scanner',required=True,
                    help='Scanner this physlog was acquired on. '
                         'Must match a value in stations_file')
parser.add_argument('--unique_root',required=True,
                    help='Unique DICOM root. Crucial to get this right to '
                         'avoid collisions')
parser.add_argument('--jpg_file',required=True,
                    help='JPG that will be affixed to the physlog to '
                         'allow conversion to DICOM')
args = parser.parse_args()


# Check that the physfile exists
if not os.path.isfile(args.physlog_file):
    raise Exception('Physlog file {} not found'.format(args.physlog_file))


# Parse the physlog filename to get path, date, and time
rxP = re.compile('(?P<path>.*)SCANPHYSLOG(?P<date>\d{8})(?P<time>\d{6}).log$')
P = rxP.search(args.physlog_file)
if P is None:
    raise Exception('Unable to parse physlog filename {}'.
    format(args.physlog_file))

# Set up remaining filenames. We'll use the same dir as the physlog, and fail
# if any are present
physpath = P.group('path')
physstem = 'SCANPHYSLOG' + P.group('date') + P.group('time')
zipfile = os.path.join(physpath,physstem + '.zip')
jpgfile = os.path.join(physpath,physstem + '.jpg')
dcmfile = os.path.join(physpath,physstem + '.dcm')
cfgfile = os.path.join(physpath,physstem + '.cfg')

if os.path.isfile(zipfile):
    raise Exception('ZIP file {} exists'.format(zipfile))
if os.path.isfile(jpgfile):
    raise Exception('JPG file {} exists'.format(jpgfile))
if os.path.isfile(cfgfile):
    raise Exception('CFG file {} exists'.format(cfgfile))
if os.path.isfile(dcmfile):
    raise Exception('DCM file {} exists'.format(dcmfile))



# Annoying but handy shortcut for knowing DICOM tags
tag_StationName = 0x00081010
tag_StudyDate = 0x00080020
tag_SeriesTime = 0x00080031
tag_SeriesInstanceUID = 0x0020000E
tag_PatientName = 0x00100010
tag_SeriesNumber = 0x00200011
tag_SeriesDescription = 0x0008103E


# Get station ID info and make sure our requested scanner is in there
with open(args.stations_file) as file:
    stations = json.load(file)
num_stationmatches = 0
for key,val in stations.iteritems():
    if val==args.physlog_scanner:
        num_stationmatches = num_stationmatches + 1
if num_stationmatches==0:
    raise Exception('No match found for station {} in {}'.
                    format(args.physlog_scanner,args.stations_file))
elif num_stationmatches>1:
    raise Exception('Multiple matches found for station {} in {}'.
                    format(args.physlog_scanner, args.stations_file))



# Query PACS for scans on this date
seriesdata = physlog_query.query(P.group('date'),args.pacs)


# Drop records that aren't from the physlog's scanner.
seriesdata = filter(lambda d:
                    stations[d[tag_StationName].value]==args.physlog_scanner,
                    seriesdata)

if len(seriesdata)==0:
    raise Exception('No studies found at {} on {}'.
                    format(args.physlog_scanner,P.group('date')))


# Compare series times vs our physlog timestamp
Pdatetime = P.group('date') + P.group('time')
physlogtime = datetime.datetime.strptime(Pdatetime,'%Y%m%d%H%M%S')

delta = [None for _ in range(0,len(seriesdata))]
mindelta = float('inf')
minindex = None

# Assume physlog started before the scan (it normally starts approx
# 60 seconds before). Find the series with the closest matching time,
# constrained to series that started later.
for c,d in enumerate(seriesdata):
    seriesdatetime = d[tag_StudyDate].value + d[tag_SeriesTime].value
    seriestime = datetime.datetime.strptime(seriesdatetime,'%Y%m%d%H%M%S.%f')
    delta[c] = (seriestime - physlogtime).total_seconds()
    if (delta[c] < mindelta) and (delta[c] > 0):
        mindelta = delta[c]
        minindex = c

# Check for finding nothing
if minindex is None:
    raise Exception('No matching {} scan found based on timestamp for {}'.
                    format(args.physlog_scanner,args.physlog_file))

# Here is our matching series
seriesmatch = seriesdata[minindex]

print('Found matching series:')
print('         Patient Name : ' + seriesmatch[tag_PatientName].value)
print('        Series Number : ' + str(seriesmatch[tag_SeriesNumber].value))
print('   Series Description : ' + seriesmatch[tag_SeriesDescription].value)
print('           Time Delta : ' + str(mindelta))

# Fail if the time difference is too large
if (mindelta < 59) or (mindelta > 61):
    raise Exception('Expected 60 sec time delta. '
                    'Was the correct scanner specified?')

# Generate new unique instance UID using our root, the 5th field of
# the Series UID that id's our scanner, and the final field of the
# Series UID that is the timestamp. Possibly only true locally.
fields = seriesmatch[tag_SeriesInstanceUID].value.split('.')
instance_uid = '.'.join((args.unique_root,'2',fields[5],fields[-1]))


# Create a cfg file for jpg2dcm, with correct UIDs and info. We are reusing
# SeriesDescription for ProtocolName on purpose, because ProtocolName comes
# back empty in the initial query.
contentdate = datetime.datetime.strftime(datetime.datetime.now(),'%Y%m%d')
contenttime = datetime.datetime.strftime(datetime.datetime.now(),'%H%M%S')
imagetype = 'SCANPHYSLOG' + P.group('date') + P.group('time')
with open(cfgfile,'w') as f:
    f.write('# Study ID\n00200010:' + seriesmatch[0x00200010].value + '\n\n')
    f.write('# Series Number\n00200011:' + str(seriesmatch[0x00200011].value) + '\n\n')
    f.write('# Patient Name\n00100010:' + seriesmatch[0x00100010].value + '\n\n')
    f.write('# Patient ID\n00100020:' + seriesmatch[0x00100020].value + '\n\n')
    f.write('# Protocol Name\n00181030:' + seriesmatch[0x0008103E].value + '\n\n')
    f.write('# Series Description\n0008103E:' + seriesmatch[0x0008103E].value + '\n\n')
    f.write('# StudyInstanceUID\n0020000D:' + seriesmatch[0x0020000D].value + '\n\n')
    f.write('# SeriesInstanceUID\n0020000E:' + seriesmatch[0x0020000E].value + '\n\n')
    f.write('# Image Type\n00080008:' + imagetype + '\n\n')
    f.write('# SOPInstanceUID\n00080018:' + instance_uid + '\n\n')
    f.write('# Content Date\n00080023:' + contentdate + '\n\n')
    f.write('# Content Time\n00080033:' + contenttime + '\n\n')
    f.write('# Manufacturer\n00080070:vuPhyslog\n')


# Some unclassy system calls to package and send our physlog DICOM

# Zip the physlog text file (new name is zipfile)
os.system(' '.join(['zip -j',zipfile,args.physlog_file]))

# Tack the dummy jpg on at the beginning (new name is jpgfile)
os.system(' '.join(['cat',args.jpg_file,zipfile,'>',jpgfile]))

# Convert the jpg to dcm. Final filename is dcmfile
os.system(' '.join(['jpg2dcm -c',cfgfile,jpgfile,dcmfile]))


# Call dcmsnd to push to PACS. We could also use pynetdicom here
# but this is trivially easy.
os.system(' '.join(['dcmsnd',args.pacs,dcmfile]))

# Clean up
os.remove(jpgfile)
os.remove(zipfile)
os.remove(cfgfile)
