import re
import pydicom
import pynetdicom

def query(studydate,pacs):
    """
    Query PACS for all scans on studydate. Doing this with pynetdicom
    is more trouble, but probably more reliable than using dcm4che
    dcmqr and parsing its text output.

    """

    # Initialise the Application Entity and add presentation context
    ae = pynetdicom.AE()
    ae.add_requested_context(pynetdicom.sop_class.
                             PatientRootQueryRetrieveInformationModelFind)

    # Create our query dataset
    ds = pydicom.dataset.Dataset()

    # Query will match on these items
    ds.StudyDate = studydate
    ds.QueryRetrieveLevel = 'SERIES'
    ds.Modality = 'MR'

    # Query will additionally return these items
    ds.add_new(0x0020000E, 'UI', '')  # Series Instance UID
    ds.add_new(0x0020000D, 'UI', '')  # Study Instance UID
    ds.add_new(0x00080031, 'TM', '')  # Series Time
    ds.add_new(0x0008103E, 'LO', '')  # Series Description
    ds.add_new(0x00200011, 'IS', '')  # Series Number
    ds.add_new(0x00081010, 'SH', '')  # Station Name
    ds.add_new(0x00400241, 'AE', '')  # Performed Station AE Title
    ds.add_new(0x00100010, 'PN', '')  # Patient Name
    ds.add_new(0x00100020, 'LO', '')  # Patient ID
    ds.add_new(0x00200010, 'SH', '')  # Study ID

    # Initialize result
    seriesdata = list()

    # Associate with peer AE
    rx = re.compile('(?P<aetitle>.+)@(?P<ip>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)')
    rxp = rx.search(pacs)
    assoc = ae.associate(rxp.group('ip'),
                         int(rxp.group('port')),
                         ae_title=rxp.group('aetitle'))

    if assoc.is_established:
        responses = assoc.send_c_find(ds, query_model='P')

        for (status, identifier) in responses:
            if status:
                if status.Status in (0xFF00, 0xFF01):
                    seriesdata = seriesdata + [identifier]
            else:
                print('Connection failed')

        assoc.release()
    else:
        print('Association rejected')

    ae.shutdown()
    return seriesdata

