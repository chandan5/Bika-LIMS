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
        "templates/productivity_analysesperformedpertotal.pt")

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

        import pdb; pdb.set_trace()
        # Query the catalog and store results in a dictionary
        analyses = catalog(parsedquery)
        if not analyses:
            message = _("No analyses matched your query")
            self.context.plone_utils.addPortalMessage(message, "error")
            return self.request.response.redirect(self.request.getURL()[:-9])

        # Need to Fetch groupby
        groupby = 'Day'
        if (groupby != ''):
            self.report_data['parameters'].append({"title": _("Grouping period"), "value": _(groupby)})

        datalines = {}
        footlines = {}
        totalcount = len(analyses)
        totalpublishedcount = 0
        totalperformedcount = 0
        for analysis in analyses:
            analysis = analysis.getObject()
            ankeyword = analysis.getKeyword()
            antitle = analysis.getServiceTitle()
            daterequested = analysis.created()

            group = ''
            if groupby == 'Day':
                group = self.ulocalized_time(daterequested)
            elif groupby == 'Week':
                group = daterequested.strftime(
                    "%Y") + ", " + daterequested.strftime("%U")
            elif groupby == 'Month':
                group = daterequested.strftime(
                    "%B") + " " + daterequested.strftime("%Y")
            elif groupby == 'Year':
                group = daterequested.strftime("%Y")
            else:
                group = ''

            dataline = {'Group': group, 'Requested': 0, 'Performed': 0,
                        'Published': 0, 'Analyses': {}}
            anline = {'Analysis': antitle, 'Requested': 0, 'Performed': 0,
                      'Published': 0}
            if (group in datalines):
                dataline = datalines[group]
                if (ankeyword in dataline['Analyses']):
                    anline = dataline['Analyses'][ankeyword]

            grouptotalcount = dataline['Requested'] + 1
            groupperformedcount = dataline['Performed']
            grouppublishedcount = dataline['Published']

            anltotalcount = anline['Requested'] + 1
            anlperformedcount = anline['Performed']
            anlpublishedcount = anline['Published']

            workflow = getToolByName(self.context, 'portal_workflow')
            arstate = workflow.getInfoFor(analysis.aq_parent, 'review_state', '')
            if (arstate == 'published'):
                anlpublishedcount += 1
                grouppublishedcount += 1
                totalpublishedcount += 1

            if (analysis.getResult()):
                anlperformedcount += 1
                groupperformedcount += 1
                totalperformedcount += 1

            group_performedrequested_ratio = float(groupperformedcount) / float(
                grouptotalcount)
            group_publishedperformed_ratio = groupperformedcount > 0 and float(
                grouppublishedcount) / float(groupperformedcount) or 0

            anl_performedrequested_ratio = float(anlperformedcount) / float(
                anltotalcount)
            anl_publishedperformed_ratio = anlperformedcount > 0 and float(
                anlpublishedcount) / float(anlperformedcount) or 0

            dataline['Requested'] = grouptotalcount
            dataline['Performed'] = groupperformedcount
            dataline['Published'] = grouppublishedcount
            dataline['PerformedRequestedRatio'] = group_performedrequested_ratio
            dataline['PerformedRequestedRatioPercentage'] = ('{0:.0f}'.format(
                group_performedrequested_ratio * 100)) + "%"
            dataline['PublishedPerformedRatio'] = group_publishedperformed_ratio
            dataline['PublishedPerformedRatioPercentage'] = ('{0:.0f}'.format(
                group_publishedperformed_ratio * 100)) + "%"

            anline['Requested'] = anltotalcount
            anline['Performed'] = anlperformedcount
            anline['Published'] = anlpublishedcount
            anline['PerformedRequestedRatio'] = anl_performedrequested_ratio
            anline['PerformedRequestedRatioPercentage'] = ('{0:.0f}'.format(
                anl_performedrequested_ratio * 100)) + "%"
            anline['PublishedPerformedRatio'] = anl_publishedperformed_ratio
            anline['PublishedPerformedRatioPercentage'] = ('{0:.0f}'.format(
                anl_publishedperformed_ratio * 100)) + "%"

            dataline['Analyses'][ankeyword] = anline
            datalines[group] = dataline

        self.report_data['datalines'] = datalines

        # Footer total data
        total_performedrequested_ratio = float(totalperformedcount) / float(
            totalcount)
        total_publishedperformed_ratio = totalperformedcount > 0 and float(
            totalpublishedcount) / float(totalperformedcount) or 0

        footline = {'Requested': totalcount,
                    'Performed': totalperformedcount,
                    'Published': totalpublishedcount,
                    'PerformedRequestedRatio': total_performedrequested_ratio,
                    'PerformedRequestedRatioPercentage': ('{0:.0f}'.format(
                        total_performedrequested_ratio * 100)) + "%",
                    'PublishedPerformedRatio': total_publishedperformed_ratio,
                    'PublishedPerformedRatioPercentage': ('{0:.0f}'.format(
                        total_publishedperformed_ratio * 100)) + "%"}

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
