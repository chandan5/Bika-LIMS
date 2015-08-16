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
from bika.lims.utils import formatDuration

class Report(BrowserView):
    template = ViewPageTemplateFile(
        "templates/report_out.pt")

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
            'headings': [],
            # parameters is a list of dictionaries:  {'title':'', 'value':''}
            # the selected parameters to be displayed in the output report
            'parameters': [],
            'formats': [],
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
        
        headings = {}
        client = logged_in_client(self.context)
        if client:
            # Always restrict to Client-only objects if this is client contact user
            parsedquery['path'] = \
                {'query': '/'.join(client.getPhysicalPath()), "level": 0}

        headings['header'] = _("Analysis turnaround times over time")
        headings['subheader'] = \
            _("The turnaround time of analyses plotted over time")
        self.report_data['headings'] = headings


        parsedquery['review_state'] = 'published'

        datalines = []
        periods = {}
        total_count = 0
        total_duration = 0
        # Need to CHANGE
        period = "Day"

        analyses = catalog(parsedquery)
        for a in analyses:
            analysis = a.getObject()
            received = analysis.created()
            if period == 'Day':
                datekey = received.strftime('%d %b %Y')
            elif period == 'Week':
                # key period on Monday
                dayofweek = received.strftime('%w')  # Sunday = 0
                if dayofweek == 0:
                    firstday = received - 6
                else:
                    firstday = received - (int(dayofweek) - 1)
                datekey = firstday.strftime(self.date_format_short)
            elif period == 'Month':
                datekey = received.strftime('%m-%d')
            if datekey not in periods:
                periods[datekey] = {'count': 0,
                                    'duration': 0,
                }
            count = periods[datekey]['count']
            duration = periods[datekey]['duration']
            count += 1
            duration += analysis.getDuration()
            periods[datekey]['duration'] = duration
            periods[datekey]['count'] = count
            total_count += 1
            total_duration += duration

        # calculate averages
        for datekey in periods.keys():
            count = periods[datekey]['count']
            duration = periods[datekey]['duration']
            ave_duration = (duration) / count
            periods[datekey]['duration'] = \
                formatDuration(self.context, ave_duration)
        
        formats = {'columns': 2,
                   'col_heads': [_('Date'),
                                 _('Turnaround time (h)'),
                   ],
                   'class': '',
        }
        self.report_data['formats'] = formats

        datalines = []

        period_keys = periods.keys()
        for period in period_keys:
            dataline = [{'value': period,
                         'class': ''}, ]
            dataline.append({'value': periods[period]['duration'],
                             'class': 'number'})
            datalines.append(dataline)

        if total_count > 0:
            ave_total_duration = total_duration / total_count
        else:
            ave_total_duration = 0
        ave_total_duration = formatDuration(self.context, ave_total_duration)

        self.report_data['datalines'] = datalines

        # footer data
        footlines = []
        footline = []
        footline = [{'value': _('Total data points'),
                     'class': 'total'}, ]

        footline.append({'value': total_count,
                         'class': 'total number'})
        footlines.append(footline)

        footline = [{'value': _('Average TAT'),
                     'class': 'total'}, ]

        footline.append({'value': ave_total_duration,
                         'class': 'total number'})
        footlines.append(footline)

        self.report_data['footlines'] = footlines
        import pdb; pdb.set_trace()
        

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
