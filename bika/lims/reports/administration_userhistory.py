from bika.lims import logger
from bika.lims.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.app.querystring import queryparser
from zope.component import getUtilitiesFor
from plone.app.querystring.interfaces import IParsedQueryIndexModifier
from plone.app.contentlisting.interfaces import IContentListing
from Products.CMFCore.utils import getToolByName
from bika.lims.utils import logged_in_client
from bika.lims import bikaMessageFactory as _

class Report(BrowserView):
    template = ViewPageTemplateFile(
        "templates/administration_userhistory.pt")

    def __init__(self, context, request={}):
        self.context = context
        self.request = request if request else context.REQUEST

    def __call__(self):
        #
        # We want to check if report data has been created, by verifying
        # that there is content in self.context.getPDF(), getCSV() or getHTML()
        #
        # If there is no content, then we will re-create it with the code
        # that we modify from original reports.
        '''
        commented for testing need to uncomment after done
        html = self.context.getHTML()
        if not html:'''
        return self.create_report()
        '''
        else:
            return html
'''

    def create_report(self):
        """Parse the parameters, retrieve data, and make it ready for the
        template to parse.
        """

        self.report_data = {
            # parameters is a list of dictionaries:  {'title':'', 'value':''}
            # the selected parameters to be displayed in the output report
            'parameters': [],
            # datalines is the data that will be rendered by the report template
            'datalines': [],
            # footlines - the report footer.
            'footlines': [],
        }

        parsedquery = queryparser.parseFormquery(
            self.context, self.context.query)

        # Check for valid indexes
        catalog = getToolByName(self.context, 'portal_catalog')
        valid_indexes = [index for index in parsedquery
                         if index in catalog.indexes()]

        # We'll ignore any invalid index, but will return an empty set if none
        # of the indexes are valid.
        if not valid_indexes:
            logger.warning(
                "Using empty query because there are no valid indexes used.")
            parsedquery = {}

        # Write the parameter list before including any automatic parameters
        # from base_query, as we don't want to print these in the report.
        for k, v in parsedquery.items():
            # XXX these must be made pretty for printing, but for now who cares!
            self.report_data['parameters'].append({'title': k, 'value': v})

        # Insert this report's base_query if one is defined in CreateReport.
        base_query = getattr(self.context, 'base_query', False)
        if base_query:
            parsedquery.update(base_query)
        # Always restrict to Client-only objects if this is client contact user
        client = logged_in_client(self.context)
        if client:
            parsedquery['path'] = \
                {'query': '/'.join(client.getPhysicalPath()), "level": 0}

        rt = getToolByName(self.context, 'portal_repository')
        mt = getToolByName(self.context, 'portal_membership')
        
        samples = catalog(parsedquery)

        datalines = []
        analyses_count = 0
        for sample in samples:
            sample = sample.getObject()

            # For each sample, retrieve the analyses and generate
            # a data line for each one
            analyses = sample.getAnalyses({})
            for analysis in analyses:
                analysis = analysis.getObject()
                dataline = {'AnalysisKeyword': analysis.getKeyword(),
                            'AnalysisTitle': analysis.getServiceTitle(),
                            'SampleID': sample.getSampleID(),
                            'SampleType': sample.getSampleType().Title(),
                            'SampleDateReceived': self.ulocalized_time(
                                sample.getDateReceived(), long_format=1),
                            'SampleSamplingDate': self.ulocalized_time(
                                sample.getSamplingDate(), long_format=1)}
                datalines.append(dataline)
                analyses_count += 1

        self.report_data['datalines'] = datalines
        # Footer total data
        footlines = []
        footline = {'TotalCount': analyses_count}
        footlines.append(footline)
        self.report_data['footlines'] = footlines

        if self.request.get('output_format', '') == 'CSV':
            import csv
            import StringIO
            import datetime

            fieldnames = [
                'SampleID',
                'SampleType',
                'SampleSamplingDate',
                'SampleDateReceived',
                'AnalysisTitle',
                'AnalysisKeyword',
            ]
            output = StringIO.StringIO()
            dw = csv.DictWriter(output, fieldnames=fieldnames)
            dw.writerow(dict((fn, fn) for fn in fieldnames))
            for row in datalines:
                dw.writerow(row)
            report_data = output.getvalue()
            output.close()
            date = datetime.datetime.now().strftime("%Y%m%d%H%M")
            setheader = self.request.RESPONSE.setHeader
            setheader('Content-Type', 'text/csv')
            setheader("Content-Disposition",
                      "attachment;filename=\"dailysamplesreceived_%s.csv\"" % date)
            self.request.RESPONSE.write(report_data)
        else:
            return self.template()
