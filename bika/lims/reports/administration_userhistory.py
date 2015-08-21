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
        "templates/administration_userhistory.pt")

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

        rt = getToolByName(self.context, 'portal_repository')
        mt = getToolByName(self.context, 'portal_membership')
        import pdb; pdb.set_trace()
        user = ''
        userfullname = ''
        if self.request.form.get('User', '') != '':
            user = self.request.form['User']
            userobj = mt.getMemberById(user)
            userfullname = userobj.getProperty('fullname') \
                           if userobj else ''
            parms.append(
                {'title': _('User'), 'value': ("%s (%s)" % (userfullname, user))})

        # Query the catalog and store results in a dictionary
        entities = self.portal_catalog(self.contentFilter)

        if not entities:
            message = _("No historical actions matched your query")
            self.context.plone_utils.addPortalMessage(message, "error")
            return self.default_template()

        datalines = []
        tmpdatalines = {}
        footlines = {}

        for entity in entities:
            entity = entity.getObject()
            entitytype = _(entity.__class__.__name__)

            # Workflow states retrieval
            for workflowid, workflow in entity.workflow_history.iteritems():
                for action in workflow:
                    actiontitle = _('Created')
                    if not action['action'] or (
                        action['action'] and action['action'] == 'create'):
                        if workflowid == 'bika_inactive_workflow':
                            continue
                        actiontitle = _('Created')
                    else:
                        actiontitle = _(action['action'])

                    if (user == '' or action['actor'] == user):
                        actorfullname = userfullname == '' and mt.getMemberById(
                            user) or userfullname
                        dataline = {'EntityNameOrId': entity.title_or_id(),
                                    'EntityAbsoluteUrl': entity.absolute_url(),
                                    'EntityCreationDate': entity.CreationDate(),
                                    'EntityModificationDate': entity.ModificationDate(),
                                    'EntityType': entitytype,
                                    'Workflow': _(workflowid),
                                    'Action': actiontitle,
                                    'ActionDate': action['time'],
                                    'ActionDateStr': self.ulocalized_time(
                                        action['time'], 1),
                                    'ActionActor': action['actor'],
                                    'ActionActorFullName': actorfullname,
                                    'ActionComments': action['comments']
                        }
                        tmpdatalines[action['time']] = dataline

            # History versioning retrieval
            history = rt.getHistoryMetadata(entity)
            if history:
                hislen = history.getLength(countPurged=False)
                for index in range(hislen):
                    meta = history.retrieve(index)['metadata']['sys_metadata']
                    metatitle = _(meta['comment'])
                    if (user == '' or meta['principal'] == user):
                        actorfullname = userfullname == '' and \
                            mt.getMemberById(user) or userfullname
                        dataline = {'EntityNameOrId': entity.title_or_id(),
                                    'EntityAbsoluteUrl': entity.absolute_url(),
                                    'EntityCreationDate': entity.CreationDate(),
                                    'EntityModificationDate': entity.ModificationDate(),
                                    'EntityType': entitytype,
                                    'Workflow': '',
                                    'Action': metatitle,
                                    'ActionDate': meta['timestamp'],
                                    'ActionDateStr': meta['timestamp'],
                                    'ActionActor': meta['principal'],
                                    'ActionActorFullName': actorfullname,
                                    'ActionComments': ''
                        }
                        tmpdatalines[meta['timestamp']] = dataline
        if len(tmpdatalines) == 0:
            message = _(
                "No actions found for user ${user}",
                mapping={"user": userfullname})
            self.context.plone_utils.addPortalMessage(message, "error")
            return self.default_template()
        else:
            # Sort datalines
            tmpkeys = tmpdatalines.keys()
            tmpkeys.sort(reverse=True)
            for index in range(len(tmpkeys)):
                datalines.append(tmpdatalines[tmpkeys[index]])

        return self.template()
