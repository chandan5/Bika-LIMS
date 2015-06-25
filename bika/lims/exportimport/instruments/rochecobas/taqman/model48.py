""" Roche Cobas Taqman 48
"""
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from . import RocheCobasTaqmanRSFParser, RocheCobasTaqmanImporter
import json
import traceback

title = "Roche Cobas - Taqman - 48"

def Import(context, request):
    """ Beckman Coulter Access 2 analysis results
    """
    infile = request.form['rochecobas_taqman_model48_file']
    fileformat = request.form['rochecobas_taqman_model48_format']
    artoapply = request.form['rochecobas_taqman_model48_artoapply']
    override = request.form['rochecobas_taqman_model48_override']
    sample = request.form.get('rochecobas_taqman_model48_sample',
                              'requestid')
    instrument = request.form.get('rochecobas_taqman_model48_instrument', None)
    errors = []
    logs = []
    warns = []

    # Load the most suitable parser according to file extension/options/etc...
    parser = None
    if not hasattr(infile, 'filename'):
        errors.append(_("No file selected"))
    if fileformat == 'rsf':
        parser = RocheCobasTaqmanRSFParser(infile)
    else:
        errors.append(t(_("Unrecognized file format ${fileformat}",
                          mapping={"fileformat": fileformat})))

    if parser:
        # Load the importer
        status = ['sample_received', 'attachment_due', 'to_be_verified']
        if artoapply == 'received':
            status = ['sample_received']
        elif artoapply == 'received_tobeverified':
            status = ['sample_received', 'attachment_due', 'to_be_verified']

        over = [False, False]
        if override == 'nooverride':
            over = [False, False]
        elif override == 'override':
            over = [True, False]
        elif override == 'overrideempty':
            over = [True, True]

        sam = ['RequestID', 'SampleID', 'ClientSampleID']
        if sample == 'requestid':
            sam = ['RequestID']
        if sample == 'sampleid':
            sam = ['SampleID']
        elif sample == 'clientsid':
            sam = ['ClientSampleID']
        elif sample == 'sample_clientsid':
            sam = ['SampleID', 'ClientSampleID']

        importer = RocheCobasTaqman48Importer(parser=parser,
                                              context=context,
                                              idsearchcriteria=sam,
                                              allowed_ar_states=status,
                                              allowed_analysis_states=None,
                                              override=over,
                                              instrument_uid=instrument)
        tbex = ''
        try:
            importer.process()
        except:
            tbex = traceback.format_exc()
        errors = importer.errors
        logs = importer.logs
        warns = importer.warns
        if tbex:
            errors.append(tbex)

    results = {'errors': errors, 'log': logs, 'warns': warns}

    return json.dumps(results)

class BeckmancoulterAccess2RSFParser(RocheCobasTaqmanRSFParser):
    def getAttachmentFileType(self):
        return "Roche Cobas Taqman 48"

class RocheCobasTaqman48Importer(RocheCobasTaqmanImporter):
    def getKeywordsToBeExcluded(self):
        return []
