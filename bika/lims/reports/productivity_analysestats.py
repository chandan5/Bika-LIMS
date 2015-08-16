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
        import pdb; pdb.set_trace()
        
        headings = {}
        headings['header'] = _("Analysis turnaround times")
        headings['subheader'] = _("The turnaround time of analyses")
        client = logged_in_client(self.context)
        if client:
            # Always restrict to Client-only objects if this is client contact user
            parsedquery['path'] = \
                {'query': '/'.join(client.getPhysicalPath()), "level": 0}

        self.report_data['headings'] = headings

        # query all the analyses and increment the counts
        count_early = 0
        mins_early = 0
        count_late = 0
        mins_late = 0
        count_undefined = 0
        services = {}

        analyses = catalog(parsedquery)

        for a in analyses:
            analysis = a.getObject()
            service_uid = analysis.getServiceUID()
            if service_uid not in services:
                services[service_uid] = {'count_early': 0,
                                         'count_late': 0,
                                         'mins_early': 0,
                                         'mins_late': 0,
                                         'count_undefined': 0,
                }
            earliness = analysis.getEarliness()
            if earliness < 0:
                count_late = services[service_uid]['count_late']
                mins_late = services[service_uid]['mins_late']
                count_late += 1
                mins_late -= earliness
                services[service_uid]['count_late'] = count_late
                services[service_uid]['mins_late'] = mins_late
            if earliness > 0:
                count_early = services[service_uid]['count_early']
                mins_early = services[service_uid]['mins_early']
                count_early += 1
                mins_early += earliness
                services[service_uid]['count_early'] = count_early
                services[service_uid]['mins_early'] = mins_early
            if earliness == 0:
                count_undefined = services[service_uid]['count_undefined']
                count_undefined += 1
                services[service_uid]['count_undefined'] = count_undefined

        # calculate averages
        for service_uid in services.keys():
            count_early = services[service_uid]['count_early']
            mins_early = services[service_uid]['mins_early']
            if count_early == 0:
                services[service_uid]['ave_early'] = ''
            else:
                avemins = (mins_early) / count_early
                services[service_uid]['ave_early'] = formatDuration(self.context,
                                                                    avemins)
            count_late = services[service_uid]['count_late']
            mins_late = services[service_uid]['mins_late']
            if count_late == 0:
                services[service_uid]['ave_late'] = ''
            else:
                avemins = mins_late / count_late
                services[service_uid]['ave_late'] = formatDuration(self.context,
                                                                   avemins)

        # and now lets do the actual report lines
        formats = {'columns': 7,
                   'col_heads': [_('Analysis'),
                                 _('Count'),
                                 _('Undefined'),
                                 _('Late'),
                                 _('Average late'),
                                 _('Early'),
                                 _('Average early'),
                   ],
                   'class': '',
        }
        self.report_data['formats'] = formats

        total_count_early = 0
        total_count_late = 0
        total_mins_early = 0
        total_mins_late = 0
        total_count_undefined = 0
        datalines = []

        for cat in catalog(portal_type='AnalysisCategory',
                      sort_on='sortable_title'):
            catline = [{'value': cat.Title,
                        'class': 'category_heading',
                        'colspan': 7}, ]
            first_time = True
            cat_count_early = 0
            cat_count_late = 0
            cat_count_undefined = 0
            cat_mins_early = 0
            cat_mins_late = 0
            for service in catalog(portal_type="AnalysisService",
                              CategoryUID=cat.UID,
                              sort_on='sortable_title'):

                dataline = [{'value': service.Title,
                             'class': 'testgreen'}, ]
                if service.UID not in services:
                    continue

                if first_time:
                    datalines.append(catline)
                    first_time = False

                # analyses found
                cat_count_early += services[service.UID]['count_early']
                cat_count_late += services[service.UID]['count_late']
                cat_count_undefined += services[service.UID]['count_undefined']
                cat_mins_early += services[service.UID]['mins_early']
                cat_mins_late += services[service.UID]['mins_late']

                count = services[service.UID]['count_early'] + \
                        services[service.UID]['count_late'] + \
                        services[service.UID]['count_undefined']

                dataline.append({'value': count,
                                 'class': 'number'})
                dataline.append(
                    {'value': services[service.UID]['count_undefined'],
                     'class': 'number'})
                dataline.append({'value': services[service.UID]['count_late'],
                                 'class': 'number'})
                dataline.append({'value': services[service.UID]['ave_late'],
                                 'class': 'number'})
                dataline.append({'value': services[service.UID]['count_early'],
                                 'class': 'number'})
                dataline.append({'value': services[service.UID]['ave_early'],
                                 'class': 'number'})

                datalines.append(dataline)

            # category totals
            dataline = [{'value': '%s - total' % (cat.Title),
                         'class': 'subtotal_label'}, ]

            dataline.append({'value': cat_count_early +
                                      cat_count_late +
                                      cat_count_undefined,
                             'class': 'subtotal_number'})

            dataline.append({'value': cat_count_undefined,
                             'class': 'subtotal_number'})

            dataline.append({'value': cat_count_late,
                             'class': 'subtotal_number'})

            if cat_count_late:
                dataitem = {'value': cat_mins_late / cat_count_late,
                            'class': 'subtotal_number'}
            else:
                dataitem = {'value': 0,
                            'class': 'subtotal_number'}

            dataline.append(dataitem)

            dataline.append({'value': cat_count_early,
                             'class': 'subtotal_number'})

            if cat_count_early:
                dataitem = {'value': cat_mins_early / cat_count_early,
                            'class': 'subtotal_number'}
            else:
                dataitem = {'value': 0,
                            'class': 'subtotal_number'}

            dataline.append(dataitem)

            total_count_early += cat_count_early
            total_count_late += cat_count_late
            total_count_undefined += cat_count_undefined
            total_mins_early += cat_mins_early
            total_mins_late += cat_mins_late

        self.report_data['datalines'] = datalines

        # footer data
        footlines = []
        footline = []
        footline = [{'value': _('Total'),
                     'class': 'total'}, ]

        footline.append({'value': total_count_early +
                                  total_count_late +
                                  total_count_undefined,
                         'class': 'total number'})

        footline.append({'value': total_count_undefined,
                         'class': 'total number'})

        footline.append({'value': total_count_late,
                         'class': 'total number'})

        if total_count_late:
            ave_mins = total_mins_late / total_count_late
            footline.append({'value': formatDuration(self.context, ave_mins),
                             'class': 'total number'})
        else:
            footline.append({'value': ''})

        footline.append({'value': total_count_early,
                         'class': 'total number'})

        if total_count_early:
            ave_mins = total_mins_early / total_count_early
            footline.append({'value': formatDuration(self.context, ave_mins),
                             'class': 'total number'})
        else:
            footline.append({'value': '',
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
