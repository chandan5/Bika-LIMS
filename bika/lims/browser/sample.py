from AccessControl import getSecurityManager
from DateTime import DateTime
from Products.Archetypes.config import REFERENCE_CATALOG
from Products.Archetypes.public import DisplayList
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from bika.lims.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import EditSample
from bika.lims import PMF
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims.browser.analyses import AnalysesView
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims.browser.header_table import HeaderTableView
from bika.lims.config import POINTS_OF_CAPTURE
from bika.lims.permissions import *
from bika.lims.utils import changeWorkflowState, tmpID
from bika.lims.utils import changeWorkflowState, to_unicode
from bika.lims.utils import getUsers
from bika.lims.utils import isActive
from bika.lims.utils import to_utf8, getHiddenAttributesForClass
from operator import itemgetter
from bika.lims.workflow import doActionFor
from plone.app.layout.globals.interfaces import IViewView
from plone.registry.interfaces import IRegistry
from zope.component import queryUtility
from zope.interface import implements
from Products.ZCTextIndex.ParseTree import ParseError
import json
import plone
import urllib

class SamplePartitionsView(BikaListingView):
    def __init__(self, context, request):
        super(SamplePartitionsView, self).__init__(context, request)
        self.context_actions = {}
        self.title = self.context.translate(_("Sample Partitions"))
        self.icon = self.portal_url + "/++resource++bika.lims.images/samplepartition_big.png"
        self.description = ""
        self.allow_edit = True
        self.show_select_all_checkbox = False
        self.show_sort_column = False
        self.show_column_toggles = False
        self.show_select_row = False
        self.show_select_column = True
        self.pagesize = 999999
        self.form_id = "partitions"

        self.columns = {
            'PartTitle': {'title': _('Partition'),
                          'sortable': False},
            'Container': {'title': _('Container'),
                          'sortable': False},
            'Preservation': {'title': _('Preservation'),
                             'sortable': False},
            ##            'Sampler': {'title': _('Sampler'),
            ##                           'sortable':False},
            ##            'DateSampled': {'title': _('Date Sampled'),
            ##                               'input_class': 'datepicker_nofuture',
            ##                               'input_width': '10',
            ##                               'sortable':False},
            'Preserver': {'title': _('Preserver'),
                          'sortable': False},
            'DatePreserved': {'title': _('Date Preserved'),
                              'input_class': 'datepicker_nofuture',
                              'input_width': '10',
                              'sortable': False}
        }
        if not self.context.absolute_url().endswith('partitions'):
            self.columns['DisposalDate'] = {'title': _('Disposal Date'),
                                               'sortable':False}
        self.columns['state_title'] = {'title': _('State'), 'sortable':False}

        self.review_states = [
            {'id':'default',
             'title': _('All'),
             'contentFilter':{},
             'columns': ['PartTitle',
                         'Container',
                         'Preservation',
##                         'Sampler',
##                         'DateSampled',
                         'Preserver',
                         'DatePreserved',
                         'state_title'],
             'transitions': [ #{'id': 'sample'},
                             {'id': 'preserve'},
                             {'id': 'receive'},
                             {'id': 'cancel'},
                             {'id': 'reinstate'}],
             'custom_actions':[{'id': 'save_partitions_button',
                                'title': _('Save')}, ],
            },
        ]
        if not self.context.absolute_url().endswith('partitions'):
            self.columns['DisposalDate'] = {'title': _('Disposal Date'),
                                               'sortable':False}

    def __call__(self):
        mtool = getToolByName(self.context, 'portal_membership')
        checkPermission = mtool.checkPermission
        if self.context.portal_type == 'AnalysisRequest':
            self.sample = self.context.getSample()
        else:
            self.sample = self.context
        if checkPermission(AddSamplePartition, self.sample):
            self.context_actions[_('Add')] = \
                {'url': self.sample.absolute_url() + '/createSamplePartition',
                 'icon': '++resource++bika.lims.images/add.png'}

        return super(SamplePartitionsView, self).__call__()

    def folderitems(self, full_objects = False):
        mtool = getToolByName(self.context, 'portal_membership')
        workflow = getToolByName(self.context, 'portal_workflow')
        checkPermission = mtool.checkPermission
        edit_states = ['sample_registered', 'to_be_sampled', 'sampled',
                       'to_be_preserved', 'sample_due', 'attachment_due',
                       'sample_received', 'to_be_verified']
        if self.context.portal_type == 'AnalysisRequest':
            self.sample = self.context.getSample()
        else:
            self.sample = self.context
        self.allow_edit = checkPermission(EditSamplePartition, self.sample) \
                    and workflow.getInfoFor(self.sample, 'review_state') in edit_states \
                    and workflow.getInfoFor(self.sample, 'cancellation_state') == 'active'
        self.show_select_column = self.allow_edit
        if self.allow_edit == False:
            self.review_states[0]['custom_actions'] = []

        pc = getToolByName(self.context, 'portal_catalog')

        containers = [({'ResultValue':o.UID,
                        'ResultText':o.title})
                      for o in pc(portal_type="Container",
                                   inactive_state="active")]
        preservations = [({'ResultValue':o.UID,
                           'ResultText':o.title})
                         for o in pc(portal_type="Preservation",
                                      inactive_state="active")]

        parts = [p for p in self.sample.objectValues()
                 if p.portal_type == 'SamplePartition']
        items = []
        for part in parts:
            # this folderitems doesn't subclass from the bika_listing.py
            # so we create items from scratch
            item = {
                'obj': part,
                'id': part.id,
                'uid': part.UID(),
                'title': part.Title(),
                'type_class': 'contenttype-SamplePartition',
                'url': part.aq_parent.absolute_url(),
                'relative_url': part.aq_parent.absolute_url(),
                'view_url': part.aq_parent.absolute_url(),
                'created': self.ulocalized_time(part.created()),
                'replace': {},
                'before': {},
                'after': {},
                'choices': {},
                'class': {},
                'allow_edit': [],
                'required': [],
            }

            state = workflow.getInfoFor(part, 'review_state')
            item['state_class'] = 'state-'+state
            item['state_title'] = _(state)

            item['PartTitle'] = part.getId()

            container = part.getContainer()
            if self.allow_edit:
                item['Container'] = container and container.UID() or ''
            else:
                item['Container'] = container and container.Title() or ''

            preservation = part.getPreservation()
            if self.allow_edit:
                item['Preservation'] = preservation and preservation.UID() or ''
            else:
                item['Preservation'] = preservation and preservation.Title() or ''

##            sampler = part.getSampler().strip()
##            item['Sampler'] = \
##                sampler and self.user_fullname(sampler) or ''
##            datesampled = part.getDateSampled()
##            item['DateSampled'] = \
##                datesampled and self.ulocalized_time(datesampled) or ''

            preserver = part.getPreserver().strip()
            item['Preserver'] = \
                preserver and self.user_fullname(preserver) or ''
            datepreserved = part.getDatePreserved()
            item['DatePreserved'] = \
                datepreserved and self.ulocalized_time(datepreserved, long_format=False) or ''

            disposaldate = part.getDisposalDate()
            item['DisposalDate'] = \
                disposaldate and self.ulocalized_time(disposaldate, long_format=False) or ''

            # inline edits for Container and Preservation
            if self.allow_edit:
                item['allow_edit'] = ['Container', 'Preservation']
            item['choices']['Preservation'] = preservations
            item['choices']['Container'] = containers

            # inline edits for Sampler and Date Sampled
##            checkPermission = self.context.portal_membership.checkPermission
##            if checkPermission(SampleSample, part) \
##                and not samplingdate > DateTime():
##                item['required'] += ['Sampler', 'DateSampled']
##                item['allow_edit'] += ['Sampler', 'DateSampled']
##                samplers = getUsers(part, ['Sampler', 'LabManager', 'Manager'])
##                getAuthenticatedMember = part.portal_membership.getAuthenticatedMember
##                username = getAuthenticatedMember().getUserName()
##                users = [({'ResultValue': u, 'ResultText': samplers.getValue(u)})
##                         for u in samplers]
##                item['choices']['Sampler'] = users
##                item['Sampler'] = sampler and sampler or \
##                    (username in samplers.keys() and username) or ''
##                item['DateSampled'] = item['DateSampled'] \
##                    or DateTime().strftime(self.date_format_short)
##                item['class']['Sampler'] = 'provisional'
##                item['class']['DateSampled'] = 'provisional'

            # inline edits for Preserver and Date Preserved
            checkPermission = self.context.portal_membership.checkPermission
            if checkPermission(PreserveSample, part):
                item['required'] += ['Preserver', 'DatePreserved']
                if self.allow_edit:
                    item['allow_edit'] += ['Preserver', 'DatePreserved']
                preservers = getUsers(part, ['Preserver', 'LabManager', 'Manager'])
                getAuthenticatedMember = part.portal_membership.getAuthenticatedMember
                username = getAuthenticatedMember().getUserName()
                users = [({'ResultValue': u, 'ResultText': preservers.getValue(u)})
                         for u in preservers]
                item['choices']['Preserver'] = users
                item['Preserver'] = preserver and preserver or \
                    (username in preservers.keys() and username) or ''
                item['DatePreserved'] = item['DatePreserved'] \
                    or DateTime().strftime(self.date_format_short)
                item['class']['Preserver'] = 'provisional'
                item['class']['DatePreserved'] = 'provisional'

            items.append(item)

        items = sorted(items, key=itemgetter('id'))

        return items

class createSamplePartition(BrowserView):
    """create a new Sample Partition without an edit form
    """
    def __call__(self):
        wf = getToolByName(self.context, 'portal_workflow')
        part = _createObjectByType("SamplePartition", self.context, tmpID())
        part.processForm()
        SamplingWorkflowEnabled = part.bika_setup.getSamplingWorkflowEnabled()
        ## We force the object to have the same state as the parent
        sample_state = wf.getInfoFor(self.context, 'review_state')
        changeWorkflowState(part, "bika_sample_workflow", sample_state)
        self.request.RESPONSE.redirect(self.context.absolute_url() +
                                       "/partitions")
        return

class SampleAnalysesView(AnalysesView):
    """ This renders the Field and Lab analyses tables for Samples
    """
    def __init__(self, context, request, **kwargs):
        AnalysesView.__init__(self, context, request)
        self.show_select_column = False
        self.allow_edit = False
        self.show_workflow_action_buttons = False
        for k,v in kwargs.items():
            self.contentFilter[k] = v
        self.columns['Request'] = {'title': _("Request"),
                                   'sortable':False}
        self.columns['Priority'] = {'title': _("Priority"),
                                   'sortable':False}
        # Add Request and Priority columns
        pos = self.review_states[0]['columns'].index('Service') + 1
        self.review_states[0]['columns'].insert(pos, 'Request')
        pos += 1
        self.review_states[0]['columns'].insert(pos, 'Priority')

    def folderitems(self):
        self.contentsMethod = self.context.getAnalyses
        items = AnalysesView.folderitems(self)
        for x in range(len(items)):
            if not items[x].has_key('obj'):
                continue
            obj = items[x]['obj']
            ar = obj.aq_parent
            items[x]['replace']['Request'] = \
                "<a href='%s'>%s</a>"%(ar.absolute_url(), ar.Title())
            items[x]['replace']['Priority'] = ' ' #TODO this space is required for it to work
        return items

class SampleEdit(BrowserView):
    """
    """

    implements(IViewView)
    template = ViewPageTemplateFile("templates/sample.pt")
    header_table = ViewPageTemplateFile("templates/header_table.pt")

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.icon = self.portal_url + "/++resource++bika.lims.images/sample_big.png"
        self.allow_edit = True

    def now(self):
        return DateTime()

    def getDefaultSpec(self):
        """ Returns 'lab' or 'client' to set the initial value of the
            specification radios
        """
        mt = getToolByName(self.context, 'portal_membership')
        pg = getToolByName(self.context, 'portal_groups')
        member = mt.getAuthenticatedMember()
        member_groups = [pg.getGroupById(group.id).getGroupName() \
                         for group in pg.getGroupsByUserId(member.id)]
        default_spec = ('Clients' in member_groups) and 'client' or 'lab'
        return default_spec

    def __call__(self):

        if 'transition' in self.request.form:
            doActionFor(self.context, self.request.form['transition'])

        ## render header table
        self.header_table = HeaderTableView(self.context, self.request)

        ## Create Sample Partitions table
        parts_table = None
        if not self.allow_edit:
            p = SamplePartitionsView(self.context, self.request)
            p.allow_edit = self.allow_edit
            p.show_select_column = self.allow_edit
            p.show_workflow_action_buttons = self.allow_edit
            p.show_column_toggles = False
            p.show_select_all_checkbox = False
            p.review_states[0]['transitions'] = [{'id': 'empty'},] # none
            parts_table = p.contents_table()
        self.parts = parts_table

        ## Create Field and Lab Analyses tables
        self.tables = {}
        if not self.allow_edit:
            for poc in POINTS_OF_CAPTURE:
                if not self.context.getAnalyses({'PointOfCapture': poc}):
                    continue
                t = SampleAnalysesView(self.context,
                                 self.request,
                                 PointOfCapture = poc,
                                 sort_on = 'ServiceTitle')
                t.form_id = "sample_%s_analyses" % poc
                if poc == 'field':
                    t.review_states[0]['columns'].remove('DueDate')
                t.show_column_toggles = False
                t.review_states[0]['transitions'] = [{'id':'submit'},
                                                     {'id':'retract'},
                                                     {'id':'verify'}]
                self.tables[POINTS_OF_CAPTURE.getValue(poc)] = t.contents_table()

        return self.template()

    def tabindex(self):
        i = 0
        while True:
            i += 1
            yield i

class SampleView(SampleEdit):
    def __call__(self):
        self.allow_edit = False
        return SampleEdit.__call__(self)

class SamplesView(BikaListingView):
    implements(IViewView)

    def __init__(self, context, request):
        super(SamplesView, self).__init__(context, request)

        request.set('disable_plone.rightcolumn', 1)

        self.contentFilter = {'portal_type': 'Sample',
                              'sort_on':'created',
                              'sort_order': 'reverse',
                              'path': {'query': "/",
                                       'level': 0 }
                              }
        self.context_actions = {}
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.allow_edit = True
        self.form_id = "samples"

        if self.view_url.find("/samples") > -1:
            self.request.set('disable_border', 1)
        else:
            self.view_url = self.view_url + "/samples"

        self.icon = self.portal_url + "/++resource++bika.lims.images/sample_big.png"
        self.title = self.context.translate(_("Samples"))
        self.description = ""

        SamplingWorkflowEnabled = self.context.bika_setup.getSamplingWorkflowEnabled()

        mtool = getToolByName(self.context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        user_is_preserver = 'Preserver' in member.getRoles()

        self.columns = {
            'SampleID': {'title': _('Sample ID'),
                         'index': 'SampleID'},
            'Client': {'title': _("Client"),
                       'toggle': True, },
            'Creator': {'title': PMF('Creator'),
                        'index': 'Creator',
                        'toggle': True},
            'Created': {'title': PMF('Date Created'),
                        'index': 'created',
                        'toggle': False},
            'Requests': {'title': _('Requests'),
                         'sortable': False,
                         'toggle': False},
            'ClientReference': {'title': _('Client Ref'),
                                'index': 'ClientReference',
                                'toggle': True},
            'ClientSampleID': {'title': _('Client SID'),
                               'index': 'ClientSampleID',
                               'toggle': True},
            'SampleTypeTitle': {'title': _('Sample Type'),
                                'index': 'SampleTypeTitle'},
            'SamplePointTitle': {'title': _('Sample Point'),
                                 'index': 'SamplePointTitle',
                                 'toggle': False},
            'StorageLocation': {'title': _('Storage Location'),
                                'toggle': False},
            'SamplingDeviation': {'title': _('Sampling Deviation'),
                                  'toggle': False},
            'AdHoc': {'title': _('Ad-Hoc'),
                      'toggle': False},
            'SamplingDate': {'title': _('Sampling Date'),
                             'index': 'SamplingDate',
                             'toggle': True},
            'DateSampled': {'title': _('Date Sampled'),
                            'index': 'DateSampled',
                            'toggle': SamplingWorkflowEnabled,
                            'input_class': 'datepicker_nofuture',
                            'input_width': '10'},
            'Sampler': {'title': _('Sampler'),
                        'toggle': SamplingWorkflowEnabled},
            'DatePreserved': {'title': _('Date Preserved'),
                              'toggle': user_is_preserver,
                              'input_class': 'datepicker_nofuture',
                              'input_width': '10'},
            'Preserver': {'title': _('Preserver'),
                          'toggle': user_is_preserver},
            'DateReceived': {'title': _('Date Received'),
                             'index': 'DateReceived',
                             'toggle': False},
            'state_title': {'title': _('State'),
                            'index': 'review_state'},
        }
        self.review_states = [
            {'id':'default',
             'title': _('Active'),
             'contentFilter':{'cancellation_state':'active',
                               'sort_on':'created'},
             'columns': ['SampleID',
                         'Client',
                         'Creator',
                         'Created',
                         'Requests',
                         'ClientReference',
                         'ClientSampleID',
                         'SampleTypeTitle',
                         'SamplePointTitle',
                         'StorageLocation',
                         'SamplingDeviation',
                         'AdHoc',
                         'SamplingDate',
                         'DateSampled',
                         'Sampler',
                         'DatePreserved',
                         'Preserver',
                         'DateReceived',
                         'state_title']},
            {'id':'sample_due',
             'title': _('Due'),
             'contentFilter': {'review_state': ('to_be_sampled',
                                                'to_be_preserved',
                                                'sample_due'),
                               'sort_on':'created',
                               'sort_order': 'reverse'},
             'columns': ['SampleID',
                         'Client',
                         'Creator',
                         'Created',
                         'Requests',
                         'ClientReference',
                         'ClientSampleID',
                         'SamplingDate',
                         'DateSampled',
                         'Sampler',
                         'DatePreserved',
                         'Preserver',
                         'SampleTypeTitle',
                         'SamplePointTitle',
                         'StorageLocation',
                         'SamplingDeviation',
                         'AdHoc',
                         'state_title']},
            {'id':'sample_received',
             'title': _('Received'),
             'contentFilter':{'review_state':'sample_received',
                              'sort_order': 'reverse',
                              'sort_on':'created'},
             'columns': ['SampleID',
                         'Client',
                         'Creator',
                         'Created',
                         'Requests',
                         'ClientReference',
                         'ClientSampleID',
                         'SampleTypeTitle',
                         'SamplePointTitle',
                         'StorageLocation',
                         'SamplingDeviation',
                         'AdHoc',
                         'SamplingDate',
                         'DateSampled',
                         'Sampler',
                         'DatePreserved',
                         'Preserver',
                         'DateReceived']},
            {'id':'expired',
             'title': _('Expired'),
             'contentFilter':{'review_state':'expired',
                              'sort_order': 'reverse',
                              'sort_on':'created'},
             'columns': ['SampleID',
                         'Client',
                         'Creator',
                         'Created',
                         'Requests',
                         'ClientReference',
                         'ClientSampleID',
                         'SampleTypeTitle',
                         'SamplePointTitle',
                         'StorageLocation',
                         'SamplingDeviation',
                         'AdHoc',
                         'SamplingDate',
                         'DateSampled',
                         'Sampler',
                         'DatePreserved',
                         'Preserver',
                         'DateReceived']},
            {'id':'disposed',
             'title': _('Disposed'),
             'contentFilter':{'review_state':'disposed',
                              'sort_order': 'reverse',
                              'sort_on':'created'},
             'columns': ['SampleID',
                         'Client',
                         'Creator',
                         'Created',
                         'Requests',
                         'ClientReference',
                         'ClientSampleID',
                         'SampleTypeTitle',
                         'SamplePointTitle',
                         'StorageLocation',
                         'SamplingDeviation',
                         'AdHoc',
                         'SamplingDate',
                         'DateSampled',
                         'Sampler',
                         'DatePreserved',
                         'Preserver',
                         'DateReceived']},
            {'id':'cancelled',
             'title': _('Cancelled'),
             'contentFilter': {'cancellation_state': 'cancelled',
                               'sort_order': 'reverse',
                               'sort_on':'created'},
             'transitions': [{'id':'reinstate'}, ],
             'columns': ['SampleID',
                         'Client',
                         'Creator',
                         'Created',
                         'Requests',
                         'ClientReference',
                         'ClientSampleID',
                         'SampleTypeTitle',
                         'SamplePointTitle',
                         'StorageLocation',
                         'SamplingDeviation',
                         'AdHoc',
                         'SamplingDate',
                         'DateReceived',
                         'DateSampled',
                         'Sampler',
                         'DatePreserved',
                         'Preserver',
                         'state_title']},
        ]

    def folderitems(self, full_objects = False):
        workflow = getToolByName(self.context, "portal_workflow")
        items = BikaListingView.folderitems(self)
        mtool = getToolByName(self.context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        translate = self.context.translate
        roles = member.getRoles()
        hideclientlink = 'RegulatoryInspector' in roles \
            and 'Manager' not in roles \
            and 'LabManager' not in roles \
            and 'LabClerk' not in roles

        for x in range(len(items)):
            if not items[x].has_key('obj'): continue
            obj = items[x]['obj']

            sample_id = obj.getSampleID()
            items[x]['SampleID'] = sample_id
            items[x]['replace']['SampleID'] = "<a href='%s'>%s</a>" % \
                (items[x]['url'], sample_id)
            items[x]['ClientReference'] = obj.getClientReference()
            items[x]['ClientSampleID'] = obj.getClientSampleID()

            st = obj.getSampleType()
            items[x]['SampleTypeTitle'] = st.Title() if st else ''
            sp = obj.getSamplePoint()
            items[x]['SamplePointTitle'] = sp.Title() if sp else ''

            items[x]['replace']['Requests'] = ",".join(
                ["<a href='%s'>%s</a>" % (o.absolute_url(), o.Title())
                 for o in obj.getAnalysisRequests()])

            items[x]['Client'] = obj.aq_parent.Title()
            if hideclientlink == False:
                items[x]['replace']['Client'] = "<a href='%s'>%s</a>" % \
                    (obj.aq_parent.absolute_url(), obj.aq_parent.Title())

            items[x]['Creator'] = self.user_fullname(obj.Creator())
            items[x]['Created'] = self.ulocalized_time(obj.created())

            items[x]['DateReceived'] = self.ulocalized_time(obj.getDateReceived())

            deviation = obj.getSamplingDeviation()
            items[x]['SamplingDeviation'] = deviation and deviation.Title() or ''

            items[x]['StorageLocation'] = obj.getStorageLocation() and obj.getStorageLocation().Title() or ''
            items[x]['AdHoc'] = obj.getAdHoc() and True or ''


            samplingdate = obj.getSamplingDate()
            items[x]['SamplingDate'] = self.ulocalized_time(samplingdate, long_format=1)

            after_icons = ''
            if obj.getSampleType().getHazardous():
                after_icons += "<img title='%s' " \
                    "src='%s/++resource++bika.lims.images/hazardous.png'>" % \
                    (t(_("Hazardous")),
                     self.portal_url)
            if obj.getSamplingDate() > DateTime():
                after_icons += "<img title='%s' " \
                    "src='%s/++resource++bika.lims.images/calendar.png' >" % \
                    (t(_("Future dated sample")),
                     self.portal_url)
            if after_icons:
                items[x]['after']['SampleID'] = after_icons

            SamplingWorkflowEnabled =\
                self.context.bika_setup.getSamplingWorkflowEnabled()

            if not samplingdate > DateTime() \
                    and SamplingWorkflowEnabled:
                datesampled = self.ulocalized_time(obj.getDateSampled())
                if not datesampled:
                    datesampled = self.ulocalized_time(DateTime())
                    items[x]['class']['DateSampled'] = 'provisional'
                sampler = obj.getSampler().strip()
                if sampler:
                    items[x]['replace']['Sampler'] = self.user_fullname(sampler)
                if 'Sampler' in member.getRoles() and not sampler:
                    sampler = member.id
                    items[x]['class']['Sampler'] = 'provisional'
            else:
                datesampled = ''
                sampler = ''
            items[x]['DateSampled'] = datesampled
            items[x]['Sampler'] = sampler

            # sampling workflow - inline edits for Sampler and Date Sampled
            checkPermission = self.context.portal_membership.checkPermission
            state = workflow.getInfoFor(obj, 'review_state')
            if state == 'to_be_sampled' \
                    and checkPermission(SampleSample, obj) \
                    and not samplingdate > DateTime():
                items[x]['required'] = ['Sampler', 'DateSampled']
                items[x]['allow_edit'] = ['Sampler', 'DateSampled']
                samplers = getUsers(obj, ['Sampler', 'LabManager', 'Manager'])
                getAuthenticatedMember = self.context.portal_membership.getAuthenticatedMember
                username = getAuthenticatedMember().getUserName()
                users = [({'ResultValue': u, 'ResultText': samplers.getValue(u)})
                         for u in samplers]
                items[x]['choices'] = {'Sampler': users}
                Sampler = sampler and sampler or \
                    (username in samplers.keys() and username) or ''
                items[x]['Sampler'] = Sampler

            # These don't exist on samples
            # the columns exist just to set "preserve" transition from lists.
            # XXX This should be a list of preservers...
            items[x]['Preserver'] = ''
            items[x]['DatePreserved'] = ''

            # inline edits for Preserver and Date Preserved
            checkPermission = self.context.portal_membership.checkPermission
            if checkPermission(PreserveSample, obj):
                items[x]['required'] = ['Preserver', 'DatePreserved']
                items[x]['allow_edit'] = ['Preserver', 'DatePreserved']
                preservers = getUsers(obj, ['Preserver', 'LabManager', 'Manager'])
                getAuthenticatedMember = self.context.portal_membership.getAuthenticatedMember
                username = getAuthenticatedMember().getUserName()
                users = [({'ResultValue': u, 'ResultText': preservers.getValue(u)})
                         for u in preservers]
                items[x]['choices'] = {'Preserver': users}
                preserver = username in preservers.keys() and username or ''
                items[x]['Preserver'] = preserver
                items[x]['DatePreserved'] = self.ulocalized_time(DateTime())
                items[x]['class']['Preserver'] = 'provisional'
                items[x]['class']['DatePreserved'] = 'provisional'

        # Hide Preservation/Sampling workflow actions if the edit columns
        # are not displayed.
        toggle_cols = self.get_toggle_cols()
        new_states = []
        for i,state in enumerate(self.review_states):
            if state['id'] == self.review_state:
                if 'Sampler' not in toggle_cols \
                   or 'DateSampled' not in toggle_cols:
                    if 'hide_transitions' in state:
                        state['hide_transitions'].append('sample')
                    else:
                        state['hide_transitions'] = ['sample',]
                if 'Preserver' not in toggle_cols \
                   or 'DatePreserved' not in toggle_cols:
                    if 'hide_transitions' in state:
                        state['hide_transitions'].append('preserve')
                    else:
                        state['hide_transitions'] = ['preserve',]
            new_states.append(state)
        self.review_states = new_states

        return items


class ajaxGetSampleTypeInfo(BrowserView):
    def __call__(self):
        plone.protect.CheckAuthenticator(self.request)
        uid = self.request.get('UID', '')
        title = self.request.get('Title', '')
        ret = {
               'UID': '',
               'Title': '',
               'Prefix': '',
               'Hazardous': '',
               'SampleMatrixUID': '',
               'SampleMatrixTitle': '',
               'MinimumVolume':  '',
               'ContainerTypeUID': '',
               'ContainerTypeTitle': '',
               'SamplePoints': ('',),
               'StorageLocations': ('',),
               }
        proxies = None
        if uid:
            try:
                pc = getToolByName(self.context, 'portal_catalog')
                proxies = pc(UID=uid)
            except ParseError:
                pass
        elif title:
            try:
                pc = getToolByName(self.context, 'portal_catalog')
                proxies = pc(portal_type='SampleType', title=title)
            except ParseError:
                pass

        if proxies and len(proxies) == 1:
            st = proxies[0].getObject();
            ret = {
               'UID': st.UID(),
               'Title': st.Title(),
               'Prefix': st.getPrefix(),
               'Hazardous': st.getHazardous(),
               'SampleMatrixUID': st.getSampleMatrix() and \
                                  st.getSampleMatrix().UID() or '',
               'SampleMatrixTitle': st.getSampleMatrix() and \
                                  st.getSampleMatrix().Title() or '',
               'MinimumVolume':  st.getMinimumVolume(),
               'ContainerTypeUID': st.getContainerType() and \
                                   st.getContainerType().UID() or '',
               'ContainerTypeTitle': st.getContainerType() and \
                                     st.getContainerType().Title() or '',
               'SamplePoints': dict((sp.UID(),sp.Title()) for sp in st.getSamplePoints()),
               'StorageLocations': dict((sp.UID(),sp.Title()) for sp in st.getStorageLocations()),
               }

        return json.dumps(ret)
