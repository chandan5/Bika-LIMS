from AccessControl import getSecurityManager
from Products.CMFCore.permissions import ModifyPortalContent
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims.utils import getUsers
from bika.lims.permissions import *
from bika.lims.utils import to_utf8, getUsers
from DateTime import DateTime
from Products.Archetypes import PloneMessageFactory as PMF
from plone.app.layout.globals.interfaces import IViewView
from Products.CMFCore.utils import getToolByName
from zope.interface import implements


class AnalysisRequestsView(BikaListingView):
    """Base for all lists of ARs
    """
    implements(IViewView)

    def __init__(self, context, request):
        super(AnalysisRequestsView, self).__init__(context, request)

        request.set('disable_plone.rightcolumn', 1)

        self.contentFilter = {'portal_type': 'AnalysisRequest',
                              'sort_on': 'created',
                              'sort_order': 'reverse',
                              'path': {"query": "/", "level": 0}
                              }

        self.context_actions = {}

        if self.context.portal_type == "AnalysisRequestsFolder":
            self.request.set('disable_border', 1)

        if self.view_url.find("analysisrequests") == -1:
            self.view_url = self.view_url + "/analysisrequests"

        self.allow_edit = True

        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = True
        self.form_id = "analysisrequests"

        self.icon = self.portal_url + "/++resource++bika.lims.images/analysisrequest_big.png"
        self.title = self.context.translate(_("Analysis Requests"))
        self.description = ""

        SamplingWorkflowEnabled = self.context.bika_setup.getSamplingWorkflowEnabled()

        mtool = getToolByName(self.context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        user_is_preserver = 'Preserver' in member.getRoles()

        self.columns = {
            'RequestID': {'title': _('Request ID'),
                             'index': 'RequestID'},
            'ClientOrderNumber': {'title': _('Client Order'),
                                     'index': 'ClientOrderNumber',
                                     'toggle': True},
            'Creator': {'title': PMF('Creator'),
                                     'index': 'Creator',
                                     'toggle': True},
            'Created': {'title': PMF('Date Created'),
                        'index': 'created',
                        'toggle': False},
            'getSample': {'title': _("Sample"),
                          'toggle': True, },
            'BatchID': {'title': _("Batch ID"), 'toggle': True},
            'SubGroup': {'title': _('Sub-group')},
            'Client': {'title': _('Client'),
                       'toggle': True},
            'ClientReference': {'title': _('Client Ref'),
                                   'index': 'ClientReference',
                                   'toggle': True},
            'ClientSampleID': {'title': _('Client SID'),
                                  'index': 'ClientSampleID',
                                  'toggle': True},
            'ClientContact': {'title': _('Contact'),
                                 'toggle': False},
            'SampleTypeTitle': {'title': _('Sample Type'),
                                   'index': 'SampleTypeTitle',
                                   'toggle': True},
            'SamplePointTitle': {'title': _('Sample Point'),
                                    'index': 'SamplePointTitle',
                                    'toggle': False},
            'getStorageLocation': {'title': _('Storage Location'),
                                    'toggle': False},
            'SamplingDeviation': {'title': _('Sampling Deviation'),
                                  'toggle': False},
            'Priority': {'title': _('Priority'),
                            'toggle': True,
                            'index': 'Priority',
                            'sortable': True},
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
            'getDatePreserved': {'title': _('Date Preserved'),
                                 'toggle': user_is_preserver,
                                 'input_class': 'datepicker_nofuture',
                                 'input_width': '10',
                                 'sortable': False},  # no datesort without index
            'Preserver': {'title': _('Preserver'),
                             'toggle': user_is_preserver},
            'DateReceived': {'title': _('Date Received'),
                                'index': 'DateReceived',
                                'toggle': False},
            'DatePublished': {'title': _('Date Published'),
                                 'index': 'DatePublished',
                                 'toggle': False},
            'state_title': {'title': _('State'),
                            'index': 'review_state'},
            'ProfileTitle': {'title': _('Profile'),
                                'index': 'ProfileTitle',
                                'toggle': False},
            'getAnalysesNum': {'title': _('Number of Analyses'),
                               'index': 'getAnalysesNum',
                               'sortable': True,
                               'toggle': False},
            'getTemplateTitle': {'title': _('Template'),
                                 'index': 'getTemplateTitle',
                                 'toggle': False},
        }
        self.review_states = [
            {'id': 'default',
             'title': _('Active'),
             'contentFilter': {'cancellation_state': 'active',
                              'sort_on': 'created',
                              'sort_order': 'reverse'},
             'transitions': [{'id': 'sample'},
                             {'id': 'preserve'},
                             {'id': 'receive'},
                             {'id': 'retract'},
                             {'id': 'verify'},
                             {'id': 'prepublish'},
                             {'id': 'publish'},
                             {'id': 'republish'},
                             {'id': 'cancel'},
                             {'id': 'reinstate'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientContact',
                        'ClientSampleID',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'SamplingDate',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'DateReceived',
                        'getAnalysesNum',
                        'state_title']},
            {'id': 'sample_due',
             'title': _('Due'),
             'contentFilter': {'review_state': ('to_be_sampled',
                                                'to_be_preserved',
                                                'sample_due'),
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'sample'},
                             {'id': 'preserve'},
                             {'id': 'receive'},
                             {'id': 'cancel'},
                             {'id': 'reinstate'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'getAnalysesNum',
                        'state_title']},
           {'id': 'sample_received',
             'title': _('Received'),
             'contentFilter': {'review_state': 'sample_received',
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'prepublish'},
                             {'id': 'cancel'},
                             {'id': 'reinstate'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'getAnalysesNum',
                        'DateReceived']},
            {'id': 'to_be_verified',
             'title': _('To be verified'),
             'contentFilter': {'review_state': 'to_be_verified',
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'retract'},
                             {'id': 'verify'},
                             {'id': 'prepublish'},
                             {'id': 'cancel'},
                             {'id': 'reinstate'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'getAnalysesNum',
                        'DateReceived']},
            {'id': 'verified',
             'title': _('Verified'),
             'contentFilter': {'review_state': 'verified',
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'publish'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'getAnalysesNum',
                        'DateReceived']},
            {'id': 'published',
             'title': _('Published'),
             'contentFilter': {'review_state': ('published', 'invalid'),
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'republish'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'DateReceived',
                        'getAnalysesNum',
                        'DatePublished']},
            {'id': 'cancelled',
             'title': _('Cancelled'),
             'contentFilter': {'cancellation_state': 'cancelled',
                               'review_state': ('to_be_sampled', 'to_be_preserved',
                                                'sample_due', 'sample_received',
                                                'to_be_verified', 'attachment_due',
                                                'verified', 'published'),
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'reinstate'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'DateReceived',
                        'DatePublished',
                        'getAnalysesNum',
                        'state_title']},
            {'id': 'invalid',
             'title': _('Invalid'),
             'contentFilter': {'review_state': 'invalid',
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [],
             'custom_actions': [],
             'columns':['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'DateReceived',
                        'getAnalysesNum',
                        'DatePublished']},
            {'id': 'assigned',
             'title': "<img title='%s'\
                       src='%s/++resource++bika.lims.images/assigned.png'/>" % (
                       t(_("Assigned")), self.portal_url),
             'contentFilter': {'worksheetanalysis_review_state': 'assigned',
                               'review_state': ('sample_received', 'to_be_verified',
                                                'attachment_due', 'verified',
                                                'published'),
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'retract'},
                             {'id': 'verify'},
                             {'id': 'prepublish'},
                             {'id': 'publish'},
                             {'id': 'republish'},
                             {'id': 'cancel'},
                             {'id': 'reinstate'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'DateReceived',
                        'getAnalysesNum',
                        'state_title']},
            {'id': 'unassigned',
             'title': "<img title='%s'\
                       src='%s/++resource++bika.lims.images/unassigned.png'/>" % (
                       t(_("Unassigned")), self.portal_url),
             'contentFilter': {'worksheetanalysis_review_state': 'unassigned',
                               'review_state': ('sample_received', 'to_be_verified',
                                                'attachment_due', 'verified',
                                                'published'),
                               'sort_on': 'created',
                               'sort_order': 'reverse'},
             'transitions': [{'id': 'receive'},
                             {'id': 'retract'},
                             {'id': 'verify'},
                             {'id': 'prepublish'},
                             {'id': 'publish'},
                             {'id': 'republish'},
                             {'id': 'cancel'},
                             {'id': 'reinstate'}],
             'custom_actions': [],
             'columns': ['RequestID',
                        'getSample',
                        'BatchID',
                        'SubGroup',
                        'Client',
                        'ProfileTitle',
                        'getTemplateTitle',
                        'Creator',
                        'Created',
                        'ClientOrderNumber',
                        'ClientReference',
                        'ClientSampleID',
                        'ClientContact',
                        'SampleTypeTitle',
                        'SamplePointTitle',
                        'getStorageLocation',
                        'SamplingDeviation',
                        'Priority',
                        'AdHoc',
                        'SamplingDate',
                        'DateSampled',
                        'Sampler',
                        'getDatePreserved',
                        'Preserver',
                        'DateReceived',
                        'getAnalysesNum',
                        'state_title']},
            ]

    def folderitems(self, full_objects=False):
        workflow = getToolByName(self.context, "portal_workflow")
        items = BikaListingView.folderitems(self)
        mtool = getToolByName(self.context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        roles = member.getRoles()
        hideclientlink = 'RegulatoryInspector' in roles \
            and 'Manager' not in roles \
            and 'LabManager' not in roles \
            and 'LabClerk' not in roles

        for x in range(len(items)):
            if 'obj' not in items[x]:
                continue
            obj = items[x]['obj']
            sample = obj.getSample()

            if getSecurityManager().checkPermission(EditResults, obj):
                url = obj.absolute_url() + "/manage_results"
            else:
                url = obj.absolute_url()

            items[x]['Client'] = obj.aq_parent.Title()
            if (hideclientlink is False):
                items[x]['replace']['Client'] = "<a href='%s'>%s</a>" % \
                    (obj.aq_parent.absolute_url(), obj.aq_parent.Title())
            items[x]['Creator'] = self.user_fullname(obj.Creator())
            items[x]['RequestID'] = obj.getRequestID()
            items[x]['replace']['RequestID'] = "<a href='%s'>%s</a>" % \
                 (url, items[x]['RequestID'])
            items[x]['getSample'] = sample
            items[x]['replace']['getSample'] = \
                "<a href='%s'>%s</a>" % (sample.absolute_url(), sample.Title())

            if obj.getAnalysesNum():
                items[x]['getAnalysesNum'] = str(obj.getAnalysesNum()[0]) + '/' + str(obj.getAnalysesNum()[1])
            else:
                items[x]['getAnalysesNum'] = ''

            batch = obj.getBatch()
            if batch:
                items[x]['BatchID'] = batch.getBatchID()
                items[x]['replace']['BatchID'] = "<a href='%s'>%s</a>" % \
                     (batch.absolute_url(), items[x]['BatchID'])
            else:
                items[x]['BatchID'] = ''

            val = obj.Schema().getField('SubGroup').get(obj)
            items[x]['SubGroup'] = val.Title() if val else ''

            samplingdate = obj.getSample().getSamplingDate()
            items[x]['SamplingDate'] = self.ulocalized_time(samplingdate, long_format=1)
            items[x]['DateReceived'] = self.ulocalized_time(obj.getDateReceived())
            items[x]['DatePublished'] = self.ulocalized_time(obj.getDatePublished())

            deviation = sample.getSamplingDeviation()
            items[x]['SamplingDeviation'] = deviation and deviation.Title() or ''
            priority = obj.getPriority()
            items[x]['Priority'] = '' # priority.Title()

            items[x]['getStorageLocation'] = sample.getStorageLocation() and sample.getStorageLocation().Title() or ''
            items[x]['AdHoc'] = sample.getAdHoc() and True or ''

            after_icons = ""
            state = workflow.getInfoFor(obj, 'worksheetanalysis_review_state')
            if state == 'assigned':
                after_icons += "<img src='%s/++resource++bika.lims.images/worksheet.png' title='%s'/>" % \
                    (self.portal_url, t(_("All analyses assigned")))
            if workflow.getInfoFor(obj, 'review_state') == 'invalid':
                after_icons += "<img src='%s/++resource++bika.lims.images/delete.png' title='%s'/>" % \
                    (self.portal_url, t(_("Results have been withdrawn")))
            if obj.getLate():
                after_icons += "<img src='%s/++resource++bika.lims.images/late.png' title='%s'>" % \
                    (self.portal_url, t(_("Late Analyses")))
            if samplingdate > DateTime():
                after_icons += "<img src='%s/++resource++bika.lims.images/calendar.png' title='%s'>" % \
                    (self.portal_url, t(_("Future dated sample")))
            if obj.getInvoiceExclude():
                after_icons += "<img src='%s/++resource++bika.lims.images/invoice_exclude.png' title='%s'>" % \
                    (self.portal_url, t(_("Exclude from invoice")))
            if sample.getSampleType().getHazardous():
                after_icons += "<img src='%s/++resource++bika.lims.images/hazardous.png' title='%s'>" % \
                    (self.portal_url, t(_("Hazardous")))
            if after_icons:
                items[x]['after']['RequestID'] = after_icons

            items[x]['Created'] = self.ulocalized_time(obj.created())

            contact = obj.getContact()
            if contact:
                items[x]['ClientContact'] = contact.Title()
                items[x]['replace']['ClientContact'] = "<a href='%s'>%s</a>" % \
                    (contact.absolute_url(), contact.Title())
            else:
                items[x]['ClientContact'] = ""

            SamplingWorkflowEnabled = sample.getSamplingWorkflowEnabled()
            if SamplingWorkflowEnabled and not samplingdate > DateTime():
                datesampled = self.ulocalized_time(sample.getDateSampled())
                if not datesampled:
                    datesampled = self.ulocalized_time(
                        DateTime(),
                        long_format=1)
                    items[x]['class']['DateSampled'] = 'provisional'
                sampler = sample.getSampler().strip()
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
                samplers = getUsers(sample, ['Sampler', 'LabManager', 'Manager'])
                username = member.getUserName()
                users = [({'ResultValue': u, 'ResultText': samplers.getValue(u)})
                         for u in samplers]
                items[x]['choices'] = {'Sampler': users}
                Sampler = sampler and sampler or \
                    (username in samplers.keys() and username) or ''
                items[x]['Sampler'] = Sampler

            # These don't exist on ARs
            # XXX This should be a list of preservers...
            items[x]['Preserver'] = ''
            items[x]['getDatePreserved'] = ''

            # inline edits for Preserver and Date Preserved
            checkPermission = self.context.portal_membership.checkPermission
            if checkPermission(PreserveSample, obj):
                items[x]['required'] = ['Preserver', 'getDatePreserved']
                items[x]['allow_edit'] = ['Preserver', 'getDatePreserved']
                preservers = getUsers(obj, ['Preserver', 'LabManager', 'Manager'])
                username = member.getUserName()
                users = [({'ResultValue': u, 'ResultText': preservers.getValue(u)})
                         for u in preservers]
                items[x]['choices'] = {'Preserver': users}
                preserver = username in preservers.keys() and username or ''
                items[x]['Preserver'] = preserver
                items[x]['getDatePreserved'] = self.ulocalized_time(
                    DateTime(),
                    long_format=1)
                items[x]['class']['Preserver'] = 'provisional'
                items[x]['class']['getDatePreserved'] = 'provisional'

            # Submitting user may not verify results
            if items[x]['review_state'] == 'to_be_verified' and \
               not checkPermission(VerifyOwnResults, obj):
                self_submitted = False
                try:
                    review_history = list(workflow.getInfoFor(obj, 'review_history'))
                    review_history.reverse()
                    for event in review_history:
                        if event.get('action') == 'submit':
                            if event.get('actor') == member.getId():
                                self_submitted = True
                            break
                    if self_submitted:
                        items[x]['after']['state_title'] = \
                             "<img src='++resource++bika.lims.images/submitted-by-current-user.png' title='%s'/>" % \
                             t(_("Cannot verify: Submitted by current user"))
                except Exception:
                    pass

        # Hide Preservation/Sampling workflow actions if the edit columns
        # are not displayed.
        toggle_cols = self.get_toggle_cols()
        new_states = []
        for i, state in enumerate(self.review_states):
            if state['id'] == self.review_state:
                if 'Sampler' not in toggle_cols \
                   or 'DateSampled' not in toggle_cols:
                    if 'hide_transitions' in state:
                        state['hide_transitions'].append('sample')
                    else:
                        state['hide_transitions'] = ['sample', ]
                if 'Preserver' not in toggle_cols \
                   or 'getDatePreserved' not in toggle_cols:
                    if 'hide_transitions' in state:
                        state['hide_transitions'].append('preserve')
                    else:
                        state['hide_transitions'] = ['preserve', ]
            new_states.append(state)
        self.review_states = new_states

        return items

    @property
    def copy_to_new_allowed(self):
        mtool = getToolByName(self.context, 'portal_membership')
        if mtool.checkPermission(ManageAnalysisRequests, self.context) \
            or mtool.checkPermission(ModifyPortalContent, self.context):
            return True
        return False

    def __call__(self):
        # Only "BIKA: ManageAnalysisRequests" may see the copy to new button.
        # elsewhere it is hacked in where required.
        if self.copy_to_new_allowed:
            review_states = []
            for review_state in self.review_states:
                review_state.get('custom_actions', []).extend(
                    [{'id': 'copy_to_new',
                      'title': _('Copy to new'),
                      'url': 'workflow_action?action=copy_to_new'}, ])
                review_states.append(review_state)
            self.review_states = review_states
        return super(AnalysisRequestsView, self).__call__()
