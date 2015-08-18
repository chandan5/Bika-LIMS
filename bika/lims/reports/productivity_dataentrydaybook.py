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
        "templates/productivity_dataentrydaybook.pt")

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

        # Query the catalog and store results in a dictionary
        ars = catalog(parsedquery)
        if not ars:
            message = _("No Analysis Requests matched your query")
            self.context.plone_utils.addPortalMessage(message, "error")
            return self.request.response.redirect(self.request.getURL()[:-9])

        datalines = {}
        footlines = {}
        totalcreatedcount = len(ars)
        totalreceivedcount = 0
        totalpublishedcount = 0
        totalanlcount = 0
        totalreceptionlag = 0
        totalpublicationlag = 0

        for ar in ars:
            ar = ar.getObject()
            datecreated = ar.created()
            datereceived = ar.getDateReceived()
            datepublished = ar.getDatePublished()
            receptionlag = 0
            publicationlag = 0
            anlcount = len(ar.getAnalyses())

            dataline = {
                "AnalysisRequestID": ar.getRequestID(),
                "DateCreated": self.ulocalized_time(datecreated),
                "DateReceived": self.ulocalized_time(datereceived),
                "DatePublished": self.ulocalized_time(datepublished),
                "ReceptionLag": receptionlag,
                "PublicationLag": publicationlag,
                "TotalLag": receptionlag + publicationlag,
                "BatchID": ar.getBatch().getId() if ar.getBatch() else '',
                "SampleID": ar.getSample().Title(),
                "SampleType": ar.getSampleTypeTitle(),
                "NumAnalyses": anlcount,
                "ClientID": ar.aq_parent.id,
                "Creator": ar.Creator(),
                "Remarks": ar.getRemarks()
            }

            datalines[ar.getRequestID()] = dataline

            totalreceivedcount += ar.getDateReceived() and 1 or 0
            totalpublishedcount += ar.getDatePublished() and 1 or 0
            totalanlcount += anlcount
            totalreceptionlag += receptionlag
            totalpublicationlag += publicationlag

        self.report_data['datalines'] = datalines

        # Footer total data
        totalreceivedcreated_ratio = float(totalreceivedcount) / float(
            totalcreatedcount)
        totalpublishedcreated_ratio = float(totalpublishedcount) / float(
            totalcreatedcount)
        totalpublishedreceived_ratio = totalreceivedcount and float(
            totalpublishedcount) / float(totalreceivedcount) or 0

        footline = {'Created': totalcreatedcount,
                    'Received': totalreceivedcount,
                    'Published': totalpublishedcount,
                    'ReceivedCreatedRatio': totalreceivedcreated_ratio,
                    'ReceivedCreatedRatioPercentage': ('{0:.0f}'.format(
                        totalreceivedcreated_ratio * 100)) + "%",
                    'PublishedCreatedRatio': totalpublishedcreated_ratio,
                    'PublishedCreatedRatioPercentage': ('{0:.0f}'.format(
                        totalpublishedcreated_ratio * 100)) + "%",
                    'PublishedReceivedRatio': totalpublishedreceived_ratio,
                    'PublishedReceivedRatioPercentage': ('{0:.0f}'.format(
                        totalpublishedreceived_ratio * 100)) + "%",
                    'AvgReceptionLag': (
                    '{0:.1f}'.format(totalreceptionlag / totalcreatedcount)),
                    'AvgPublicationLag': (
                    '{0:.1f}'.format(totalpublicationlag / totalcreatedcount)),
                    'AvgTotalLag': ('{0:.1f}'.format((
                                                     totalreceptionlag + totalpublicationlag) / totalcreatedcount)),
                    'NumAnalyses': totalanlcount
        }

        footlines['Total'] = footline
        
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
