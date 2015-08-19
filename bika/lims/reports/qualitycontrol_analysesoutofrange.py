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
from bika.lims.utils import isAttributeHidden

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
            'footings': [],
            'footnotes': []
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
        headings['header'] = _("Analyses out of range")
        headings['subheader'] = _("Analyses results out of specified range")
        self.report_data['headings'] = headings

        client = logged_in_client(self.context)
        if client:
            # Always restrict to Client-only objects if this is client contact user
            parsedquery['path'] = \
                {'query': '/'.join(client.getPhysicalPath()), "level": 0}
        

        # and now lets do the actual report lines
        col_heads = [_('Client'),
                     _('Request'),
                     _('Sample type'),
                     _('Sample point'),
                     _('Category'),
                     _('Analysis'),
                     _('Result'),
                     _('Min'),
                     _('Max'),
                     _('Status'),
        ]
        if isAttributeHidden('Sample', 'SamplePoint'):
            col_heads.remove(_('Sample point'))

        formats = {'columns': 10,
                   'col_heads': col_heads,
                   'class': '',
        }
        self.report_data['formats'] = formats

        count_all = 0
        datalines = []

        for a_proxy in catalog(parsedquery):
            analysis = a_proxy.getObject()
            if analysis.getResult():
                try:
                    result = float(analysis.getResult())
                except:
                    continue
            else:
                continue

            keyword = analysis.getKeyword()

            # determine which specs to use for this particular analysis
            # 1) if a spec is given in the query form, use it.
            # 2) if a spec is entered directly on the analysis, use it.
            # otherwise just continue to the next object.
            spec_dict = False
            if spec_obj:
                rr = spec_obj.getResultsRangeDict()
                if keyword in rr:
                    spec_dict = rr[keyword]
            else:
                ar = analysis.aq_parent
                rr = dicts_to_dict(ar.getResultsRange(), 'keyword')
                if keyword in rr:
                    spec_dict = rr[keyword]
                else:
                    continue
            if not spec_dict:
                continue
            try:
                spec_min = float(spec_dict['min'])
                spec_max = float(spec_dict['max'])
            except ValueError:
                continue
            if spec_min <= result <= spec_max:
                continue

            # check if in shoulder: out of range, but in acceptable
            # error percentage
            shoulder = False
            error = 0
            try:
                error = float(spec_dict.get('error', '0'))
            except:
                error = 0
                pass
            error_amount = (result / 100) * error
            error_min = result - error_amount
            error_max = result + error_amount
            if ((result < spec_min) and (error_max >= spec_min)) or \
                    ((result > spec_max) and (error_min <= spec_max)):
                shoulder = True

            dataline = []

            dataitem = {'value': analysis.getClientTitle()}
            dataline.append(dataitem)

            dataitem = {'value': analysis.getRequestID()}
            dataline.append(dataitem)

            dataitem = {'value': analysis.aq_parent.getSampleTypeTitle()}
            dataline.append(dataitem)

            if isAttributeHidden('Sample', 'SamplePoint'):
                dataitem = {'value': analysis.aq_parent.getSamplePointTitle()}
                dataline.append(dataitem)

            dataitem = {'value': analysis.getCategoryTitle()}
            dataline.append(dataitem)

            dataitem = {'value': analysis.getServiceTitle()}
            dataline.append(dataitem)

            if shoulder:
                dataitem = {'value': analysis.getResult(),
                            'img_after': '++resource++bika.lims.images/exclamation.png'}
            else:
                dataitem = {'value': analysis.getResult()}

            dataline.append(dataitem)

            dataitem = {'value': spec_dict['min']}
            dataline.append(dataitem)

            dataitem = {'value': spec_dict['max']}
            dataline.append(dataitem)

            state = wf_tool.getInfoFor(analysis, 'review_state', '')
            review_state = wf_tool.getTitleForStateOnType(
                state, 'Analysis')
            dataitem = {'value': review_state}
            dataline.append(dataitem)

            datalines.append(dataline)

            count_all += 1

        self.report_data['datalines'] = datalines
        
        # table footer data
        footlines = []
        footline = []
        footitem = {'value': _('Number of analyses out of range for period'),
                    'colspan': 9,
                    'class': 'total_label'}
        footline.append(footitem)
        footitem = {'value': count_all}
        footline.append(footitem)
        footlines.append(footline)

        # report footer data
        footnotes = []
        footline = []
        footitem = {'value': _('Analysis result within error range'),
                    'img_before': '++resource++bika.lims.images/exclamation.png'
        }
        footline.append(footitem)
        footnotes.append(footline)

        self.report_data['footnotes'] = footnotes
        self.report_data['footings'] = footlines
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
