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
        "templates/productivity_samplesreceivedvsreported.pt")

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

        samples = catalog(parsedquery)

        datalines = {}
        footlines = {}
        total_received_count = 0
        total_published_count = 0

        for sample in samples:
            sample = sample.getObject()

            # For each sample, retrieve check is has results published
            # and add it to datalines
            published = False
            analyses = sample.getAnalyses({})
            for analysis in analyses:
                analysis = analysis.getObject()
                if not (analysis.getDatePublished() is None):
                    published = True
                    break

            datereceived = sample.getDateReceived()
            monthyear = datereceived.strftime("%B") + " " + datereceived.strftime(
                "%Y")
            received = 1
            publishedcnt = published and 1 or 0
            if (monthyear in datalines):
                received = datalines[monthyear]['ReceivedCount'] + 1
                publishedcnt = published and datalines[monthyear][
                                                 'PublishedCount'] + 1 or \
                               datalines[monthyear]['PublishedCount']
            ratio = publishedcnt / received
            dataline = {'MonthYear': monthyear,
                        'ReceivedCount': received,
                        'PublishedCount': publishedcnt,
                        'UnpublishedCount': received - publishedcnt,
                        'Ratio': ratio,
                        'RatioPercentage': '%02d' % (
                        100 * (float(publishedcnt) / float(received))) + '%'}
            datalines[monthyear] = dataline

            total_received_count += 1
            total_published_count = published and total_published_count + 1 or total_published_count

        # Footer total data
        if (total_received_count == 0):
            ratio = "undefined"
            ratioPercentage = "undefined"
        else:
            ratio = total_published_count / total_received_count
            ratioPercentage = '%02d' % (100 * (
                    float(total_published_count) / float(
                        total_received_count))) + '%'
        
        footline = {'ReceivedCount': total_received_count,
                    'PublishedCount': total_published_count,
                    'UnpublishedCount': total_received_count - total_published_count,
                    'Ratio': ratio,
                    'RatioPercentage': ratioPercentage
        }
        self.report_data['datalines'] = datalines
        # Footer total data
        footlines['Total'] = footline
        self.report_data['footlines'] = footlines

        if self.request.get('output_format', '') == 'CSV':
            import csv
            import StringIO
            import datetime
            # NEED TO CHANGE FIELDNAMES FOR DIFFERENT REPORTS 
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
