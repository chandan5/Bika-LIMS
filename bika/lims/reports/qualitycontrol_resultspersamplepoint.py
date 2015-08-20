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
from gpw import plot
import os
import tempfile
from bika.lims.utils import t, dicts_to_dict
from bika.lims.interfaces import IResultOutOfRange


class Report(BrowserView):
    template = ViewPageTemplateFile(
        "templates/qualitycontrol_resultspersamplepoint.pt")

    def __init__(self, context, request={}):
        self.context = context
        self.request = request if request else context.REQUEST

    def get_analysis_spec(self, analysis):
        rr = dicts_to_dict(analysis.aq_parent.getResultsRange(), 'keyword')
        return rr.get(analysis.getKeyword(), None)
    
    def ResultOutOfRange(self, analysis):
        """ Template wants to know, is this analysis out of range?
        We scan IResultOutOfRange adapters, and return True if any IAnalysis
        adapters trigger a result.
        """
        adapters = getAdapters((analysis, ), IResultOutOfRange)
        spec = self.get_analysis_spec(analysis)
        for name, adapter in adapters:
            if not spec:
                return False
            if adapter(specification=spec):
                return True

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
            'header': [],
            # parameters is a list of dictionaries:  {'title':'', 'value':''}
            # the selected parameters to be displayed in the output report
            'parameters': [],
            'formats': [],
            # datalines is the data that will be rendered by the report template
            'datalines': [],
            'tables': [],
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
        
        MinimumResults = self.context.bika_setup.getMinimumResults()
        warning_icon = "<img " + \
                       "src='" + self.portal_url + "/++resource++bika.lims.images/warning.png' " + \
                       "height='9' width='9'/>"
        error_icon = "<img " + \
                     "src='" + self.portal_url + "/++resource++bika.lims.images/exclamation.png' " + \
                     "height='9' width='9'/>"

        header = _("Results per sample point")
        subheader = _(
            "Analysis results for per sample point and analysis service")
        self.report_data['header'] = header
        self.report_data['subheader'] = subheader

        parameters = []
        titles = []

        client = logged_in_client(self.context)
        if client:
            # Always restrict to Client-only objects if this is client contact user
            parsedquery['path'] = \
                {'query': '/'.join(client.getPhysicalPath()), "level": 0}
        
        # Query the catalog and store analysis data in a dict
        analyses = {}
        out_of_range_count = 0
        in_shoulder_range_count = 0
        analysis_count = 0

        proxies = catalog(parsedquery)
        if not proxies:
            message = _("No analyses matched your query")
            self.context.plone_utils.addPortalMessage(message, 'error')
            return self.request.response.redirect(self.request.getURL()[:-9])

        # # Compile a list of dictionaries, with all relevant analysis data
        for analysis in proxies:
            analysis = analysis.getObject()
            result = analysis.getResult()
            client = analysis.aq_parent.aq_parent
            uid = analysis.UID()
            service = analysis.getService()
            keyword = service.getKeyword()
            service_title = "%s (%s)" % (service.Title(), keyword)
            result_in_range = self.ResultOutOfRange(analysis)

            if service_title not in analyses.keys():
                analyses[service_title] = []
            try:
                result = float(analysis.getResult())
            except:
                # XXX Unfloatable analysis results should be indicated
                continue
            analyses[service_title].append({
                'service': service,
                'obj': analysis,
                'Request ID': analysis.aq_parent.getId(),
                'Analyst': analysis.getAnalyst(),
                'Result': result,
                'Sampled': analysis.getDateSampled(),
                'Captured': analysis.getResultCaptureDate(),
                'Uncertainty': analysis.getUncertainty(),
                'result_in_range': result_in_range,
                'Unit': service.getUnit(),
                'Keyword': keyword,
                'icons': '',
            })
            analysis_count += 1

        keys = analyses.keys()
        keys.sort()

        self.report_data['parameters'] += [
            {"title": _("Total analyses"), "value": analysis_count},
        ]

        self.report_data['datalines'] = datalines
        
        plotscript = """
        set terminal png transparent truecolor enhanced size 700,350 font "Verdana, 8"
        set title "%(title)s"
        set xlabel "%(xlabel)s"
        set ylabel "%(ylabel)s"
        set key off
        #set logscale
        set timefmt "%(date_format_long)s"
        set xdata time
        set format x "%(date_format_short)s\\n%(time_format)s"
        set xrange ["%(x_start)s":"%(x_end)s"]
        set auto fix
        set offsets graph 0, 0, 1, 1
        set xtics border nomirror rotate by 90 font "Verdana, 5" offset 0,-3
        set ytics nomirror

        f(x) = mean_y
        fit f(x) 'gpw_DATAFILE_gpw' u 1:3 via mean_y
        stddev_y = sqrt(FIT_WSSR / (FIT_NDF + 1))

        plot mean_y-stddev_y with filledcurves y1=mean_y lt 1 lc rgb "#efefef",\
             mean_y+stddev_y with filledcurves y1=mean_y lt 1 lc rgb "#efefef",\
             mean_y with lines lc rgb '#ffffff' lw 3,\
             "gpw_DATAFILE_gpw" using 1:3 title 'data' with points pt 7 ps 1 lc rgb '#0000ee' lw 2,\
               '' using 1:3 smooth unique lc rgb '#aaaaaa' lw 2,\
               '' using 1:4 with lines lc rgb '#000000' lw 1,\
               '' using 1:5 with lines lc rgb '#000000' lw 1"""

        ## Compile plots and format data for display
        for service_title in keys:
            # used to calculate XY axis ranges
            result_values = [int(o['Result']) for o in analyses[service_title]]
            result_dates = [o['Sampled'] for o in analyses[service_title]]

            parms = []
            plotdata = str()

            range_min = ''
            range_max = ''

            for a in analyses[service_title]:

                a['Sampled'] = a['Sampled'].strftime(self.date_format_long) if a[
                    'Sampled'] else ''
                a['Captured'] = a['Captured'].strftime(self.date_format_long) if \
                a['Captured'] else ''

                R = a['Result']
                U = a['Uncertainty']

                a['Result'] = a['obj'].getFormattedResult()

                in_range = a['result_in_range']
                # result out of range
                if str(in_range[0]) == 'False':
                    out_of_range_count += 1
                    a['Result'] = "%s %s" % (a['Result'], error_icon)
                # result almost out of range
                if str(in_range[0]) == '1':
                    in_shoulder_range_count += 1
                    a['Result'] = "%s %s" % (a['Result'], warning_icon)

                spec = {}
                if hasattr(a["obj"], 'specification') and a["obj"].specification:
                    spec = a["obj"].specification

                plotdata += "%s\t%s\t%s\t%s\t%s\n" % (
                    a['Sampled'],
                    R,
                    spec.get("min", ""),
                    spec.get("max", ""),
                    U and U or 0,
                )
                plotdata.encode('utf-8')

            unit = analyses[service_title][0]['Unit']
            if MinimumResults <= len(dict([(d, d) for d in result_dates])):
                _plotscript = str(plotscript) % {
                    'title': "",
                    'xlabel': t(_("Date Sampled")),
                    'ylabel': unit and unit or '',
                    'x_start': "%s" % min(result_dates).strftime(
                        self.date_format_long),
                    'x_end': "%s" % max(result_dates).strftime(
                        self.date_format_long),
                    'date_format_long': self.date_format_long,
                    'date_format_short': self.date_format_short,
                    'time_format': self.time_format,
                }

                plot_png = plot(str(plotdata),
                                plotscript=str(_plotscript),
                                usefifo=False)

                # Temporary PNG data file
                fh, data_fn = tempfile.mkstemp(suffix='.png')
                os.write(fh, plot_png)
                plot_url = data_fn
                self.request['to_remove'].append(data_fn)

                plot_url = data_fn
            else:
                plot_url = ""

            table = {
                'title': "%s: %s" % (
                    t(_("Analysis Service")),
                    service_title),
                'parms': parms,
                'columns': ['Request ID',
                            'Analyst',
                            'Result',
                            'Sampled',
                            'Captured'],
                'data': analyses[service_title],
                'plot_url': plot_url,
            }

            self.report_data['tables'].append(table)

        translate = self.context.translate

        ## footnotes
        if out_of_range_count:
            msgid = _("Analyses out of range")
            self.report_data['footnotes'].append(
                "%s %s" % (error_icon, t(msgid)))
        if in_shoulder_range_count:
            msgid = _("Analyses in error shoulder range")
            self.report_data['footnotes'].append(
                "%s %s" % (warning_icon, t(msgid)))

        self.report_data['parameters'].append(
            {"title": _("Analyses out of range"),
             "value": out_of_range_count})
        self.report_data['parameters'].append(
            {"title": _("Analyses in error shoulder range"),
             "value": in_shoulder_range_count})
        import pdb; pdb.set_trace()
        return self.template()
