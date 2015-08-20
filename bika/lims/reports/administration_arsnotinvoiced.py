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
        
        headings = {}
        headings['header'] = _("Analysis requests not invoiced")
        headings['subheader'] = _(
            "Published Analysis Requests which have not been invoiced")
        self.report_data['headings'] = headings

        client = logged_in_client(self.context)
        if client:
            # Always restrict to Client-only objects if this is client contact user
            parsedquery['path'] = \
                {'query': '/'.join(client.getPhysicalPath()), "level": 0}


        count_all = 0
        datalines = []
        clients = {}
        sampletypes = {}
        samplepoints = {}
        categories = {}
        services = {}

        for ar_proxy in catalog(parsedquery):
            ar = ar_proxy.getObject()

            dataline = []

            dataitem = {'value': ar.aq_parent.Title()}
            dataline.append(dataitem)

            dataitem = {'value': ar.getRequestID()}
            dataline.append(dataitem)

            dataitem = {'value': ar.getSampleTypeTitle()}
            dataline.append(dataitem)

            dataitem = {'value': ar.getSamplePointTitle()}
            dataline.append(dataitem)

            dataitem = {'value': self.ulocalized_time(ar.getDatePublished())}
            dataline.append(dataitem)

            dataitem = {'value': ar.getTotalPrice()}
            dataline.append(dataitem)

            datalines.append(dataline)

            count_all += 1

        self.report_data['datalines'] = datalines

        # table footer data
        footlines = []
        footline = []
        footitem = {'value': _('Number of analyses retested for period'),
                    'colspan': 5,
                    'class': 'total_label'}
        footline.append(footitem)
        footitem = {'value': count_all}
        footline.append(footitem)
        footlines.append(footline)

        self.report_data['footlines'] = footlines

        # and now lets do the actual report lines
        formats = {'columns': 6,
                   'col_heads': [_('Client'), \
                                 _('Request'), \
                                 _('Sample type'), \
                                 _('Sample point'), \
                                 _('Published'), \
                                 _('Amount'), \
                       ],
                   'class': '',
        }
        self.report_data['formats'] = formats



        import pdb; pdb.set_trace()

        return self.template()
