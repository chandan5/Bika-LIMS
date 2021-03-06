
""" Bika setup handlers. """

from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims import logger
from bika.lims.config import *
from bika.lims.permissions import *
from bika.lims.interfaces \
        import IHaveNoBreadCrumbs, IARImportFolder, IARPriorities
from zope.event import notify
from zope.interface import alsoProvides
from Products.CMFEditions.Permissions import ApplyVersionControl
from Products.CMFEditions.Permissions import SaveNewVersion
from Products.CMFEditions.Permissions import AccessPreviousVersions


class Empty:
    pass


class BikaGenerator:

    def setupPortalContent(self, portal):
        """ Setup Bika site structure """

        wf = getToolByName(portal, 'portal_workflow')

        obj = portal._getOb('front-page')
        alsoProvides(obj, IHaveNoBreadCrumbs)
        mp = obj.manage_permission
        mp(permissions.View, ['Anonymous'], 1)

        # remove undesired content objects
        del_ids = []
        for obj_id in ['Members', 'news', 'events']:
            if obj_id in portal.objectIds():
                del_ids.append(obj_id)
        if del_ids:
            portal.manage_delObjects(ids=del_ids)

        # index objects - importing through GenericSetup doesn't
        for obj_id in ('clients',
                       'batches',
                       'invoices',
                       'pricelists',
                       'bika_setup',
                       'methods',
                       'analysisrequests',
                       'referencesamples',
                       'samples',
                       'supplyorders',
                       'worksheets',
                       'reports',
                       'queries',
                       'arimports',
                       ):
            try:
                obj = portal._getOb(obj_id)
                obj.unmarkCreationFlag()
                obj.reindexObject()
            except:
                pass

        bika_setup = portal._getOb('bika_setup')
        for obj_id in ('bika_analysiscategories',
                       'bika_analysisservices',
                       'bika_arpriorities',
                       'bika_attachmenttypes',
                       'bika_batchlabels',
                       'bika_calculations',
                       'bika_departments',
                       'bika_containers',
                       'bika_containertypes',
                       'bika_preservations',
                       'bika_instruments',
                       'bika_instrumenttypes',
                       'bika_analysisspecs',
                       'bika_analysisprofiles',
                       'bika_artemplates',
                       'bika_labcontacts',
                       'bika_labproducts',
                       'bika_manufacturers',
                       'bika_sampleconditions',
                       'bika_samplematrices',
                       'bika_samplingdeviations',
                       'bika_samplepoints',
                       'bika_sampletypes',
                       'bika_srtemplates',
                       'bika_storagelocations',
                       'bika_subgroups',
                       'bika_suppliers',
                       'bika_referencedefinitions',
                       'bika_worksheettemplates'):
            try:
                obj = bika_setup._getOb(obj_id)
                obj.unmarkCreationFlag()
                obj.reindexObject()
            except:
                pass

        lab = bika_setup.laboratory
        lab.edit(title=_('Laboratory'))
        lab.unmarkCreationFlag()
        lab.reindexObject()

        # Move calendar and user action to bika
# for action in portal.portal_controlpanel.listActions():
# if action.id in ('UsersGroups', 'UsersGroups2', 'bika_calendar_tool'):
# action.permissions = (ManageBika,)

    def setupGroupsAndRoles(self, portal):
        # add roles
        for role in ('LabManager',
                     'LabClerk',
                     'Analyst',
                     'Verifier',
                     'Sampler',
                     'Preserver',
                     'Publisher',
                     'Member',
                     'Reviewer',
                     'RegulatoryInspector',
                     'Client'):
            if role not in portal.acl_users.portal_role_manager.listRoleIds():
                portal.acl_users.portal_role_manager.addRole(role)
            # add roles to the portal
            portal._addRole(role)

        # Create groups
        portal_groups = portal.portal_groups

        if 'LabManagers' not in portal_groups.listGroupIds():
            try:
                portal_groups.addGroup('LabManagers', title="Lab Managers",
                       roles=['Member', 'LabManager', 'Site Administrator', ])
            except KeyError:
                portal_groups.addGroup('LabManagers', title="Lab Managers",
                       roles=['Member', 'LabManager', 'Manager', ])  # Plone < 4.1

        if 'LabClerks' not in portal_groups.listGroupIds():
            portal_groups.addGroup('LabClerks', title="Lab Clerks",
                roles=['Member', 'LabClerk'])

        if 'Analysts' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Analysts', title="Lab Technicians",
                roles=['Member', 'Analyst'])

        if 'Verifiers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Verifiers', title="Verifiers",
                roles=['Verifier'])

        if 'Samplers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Samplers', title="Samplers",
                roles=['Sampler'])

        if 'Preservers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Preservers', title="Preservers",
                roles=['Preserver'])

        if 'Publishers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Publishers', title="Publishers",
                roles=['Publisher'])

        if 'Clients' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Clients', title="Clients",
                roles=['Member', 'Client'])

        if 'Suppliers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Suppliers', title="",
                roles=['Member', ])

        if 'RegulatoryInspectors' not in portal_groups.listGroupIds():
            portal_groups.addGroup('RegulatoryInspectors', title="Regulatory Inspectors",
                roles=['Member', 'RegulatoryInspector'])

    def setupPermissions(self, portal):
        """ Set up some suggested role to permission mappings.
        """

        # Root permissions
        mp = portal.manage_permission

        mp(AccessJSONAPI, ['Manager', 'LabManager'], 0)

        mp(AddAnalysis, ['Manager', 'Owner', 'LabManager', 'LabClerk', 'Sampler'], 1)
        mp(AddAnalysisProfile, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddAnalysisRequest, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddAnalysisSpec, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddARTemplate, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddAttachment, ['Manager', 'LabManager', 'Owner' 'Analyst', 'LabClerk', 'Sampler', 'Client'], 0)
        mp(AddBatch, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddClient, ['Manager', 'Owner', 'LabManager'], 1)
        mp(AddClientFolder, ['Manager'], 1)
        mp(AddInvoice, ['Manager', 'LabManager'], 1)
        mp(AddMethod, ['Manager', 'LabManager'], 1)
        mp(AddMultifile, ['Manager', 'LabManager', 'LabClerk'], 1)
        mp(AddPricelist, ['Manager', 'Owner', 'LabManager'], 1)
        mp(AddSample, ['Manager', 'Owner', 'LabManager', 'LabClerk', 'Sampler'], 1)
        mp(AddSampleMatrix, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddSamplePartition, ['Manager', 'Owner', 'LabManager', 'LabClerk', 'Sampler'], 1)
        mp(AddSamplePoint, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddStorageLocation, ['Manager', 'Owner', 'LabManager', ], 1)
        mp(AddSamplingDeviation, ['Manager', 'Owner', 'LabManager', 'LabClerk'], 1)
        mp(AddSRTemplate, ['Manager', 'Owner', 'LabManager'], 0)
        mp(AddSubGroup, ['Manager', 'LabManager', 'LabClerk'], 0)

        mp(permissions.AddPortalContent, ['Manager', 'Owner', 'LabManager'], 1)
        mp(permissions.ListFolderContents, ['Manager', 'Owner'], 1)
        mp(permissions.FTPAccess, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 1)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'LabClerk', 'Owner'], 1)
        mp(permissions.ModifyPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Owner'], 1)
        mp(permissions.ManageUsers, ['Manager', 'LabManager', ], 1)

        mp(ApplyVersionControl, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Owner', 'RegulatoryInspector'], 1)
        mp(SaveNewVersion, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Owner', 'RegulatoryInspector'], 1)
        mp(AccessPreviousVersions, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Owner', 'RegulatoryInspector'], 1)

        mp(DispatchOrder, ['Manager', 'LabManager', 'LabClerk'], 1)
        mp(ManageARImport, ['Manager', 'LabManager', 'LabClerk'], 1)
        mp(ManageARPriority, ['Manager', 'LabManager', 'LabClerk'], 1)
        mp(ManageAnalysisRequests, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'Owner', 'RegulatoryInspector'], 1)
        mp(ManageBika, ['Manager', 'LabManager'], 1)
        mp(ManageClients, ['Manager', 'LabManager', 'LabClerk'], 1)
        mp(ManageLoginDetails, ['Manager', 'LabManager'], 1)
        mp(ManageReference, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 1)
        mp(ManageSuppliers, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 1)
        mp(ManageSamples, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'Owner', 'RegulatoryInspector'], 1)
        mp(ManageWorksheets, ['Manager', 'LabManager'], 1)
        mp(PostInvoiceBatch, ['Manager', 'LabManager', 'Owner'], 1)

        mp(CancelAndReinstate, ['Manager', 'LabManager'], 0)

        mp(VerifyOwnResults, ['Manager', ], 1)
        mp(ViewRetractedAnalyses, ['Manager', 'LabManager', 'LabClerk', 'Analyst', ], 0)

        mp(SampleSample, ['Manager', 'LabManager', 'Sampler'], 0)
        mp(PreserveSample, ['Manager', 'LabManager', 'Preserver'], 0)
        mp(ReceiveSample, ['Manager', 'LabManager', 'LabClerk', 'Sampler'], 1)
        mp(ExpireSample, ['Manager', 'LabManager', 'LabClerk'], 1)
        mp(DisposeSample, ['Manager', 'LabManager', 'LabClerk'], 1)
        mp(ImportAnalysis, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 1)
        mp(RejectWorksheet, ['Manager', 'LabManager', 'Verifier'], 1)
        mp(Retract, ['Manager', 'LabManager', 'Verifier'], 1)
        mp(Verify, ['Manager', 'LabManager', 'Verifier'], 1)
        mp(Publish, ['Manager', 'LabManager', 'Publisher'], 1)
        mp(EditSample, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'Owner'], 1)
        mp(EditAR, ['Manager', 'LabManager', 'LabClerk', 'Sampler'], 1)
        mp(EditWorksheet, ['Manager', 'LabManager', 'Analyst'], 1)
        mp(ResultsNotRequested, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 1)
        mp(ManageInvoices, ['Manager', 'LabManager', 'Owner'], 1)
        mp(ViewResults, ['Manager', 'LabManager', 'Analyst', 'Sampler', 'RegulatoryInspector'], 1)
        mp(EditResults, ['Manager', 'LabManager', 'Analyst'], 1)
        mp(EditFieldResults, ['Manager', 'LabManager', 'Sampler'], 1)
        mp(EditSamplePartition, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'Owner'], 1)

        mp('Access contents information', ['Authenticated'], 1)
        mp(permissions.View, ['Authenticated'], 1)

        mp(ImportInstrumentResults, ['Manager', 'LabManager', 'Analyst'], 1)

        mp(ViewLogTab, ['Manager', 'LabManager'], 1)

        mp = portal.bika_setup.manage_permission
        mp('Access contents information', ['Authenticated', 'Analyst'], 1)
        mp(permissions.ModifyPortalContent, ['Manager', 'LabManager'], 0)
        mp(permissions.View, ['Authenticated', 'Analyst'], 1)
        mp(ApplyVersionControl, ['Authenticated'], 1)
        mp(SaveNewVersion, ['Authenticated'], 1)
        mp(AccessPreviousVersions, ['Authenticated'], 1)
        portal.bika_setup.reindexObject()

        mp = portal.bika_setup.laboratory.manage_permission
        mp('Access contents information', ['Authenticated'], 1)
        mp(permissions.View, ['Authenticated'], 1)
        portal.bika_setup.laboratory.reindexObject()

        # /clients folder permissions

        # When modifying these defaults, look to subscribers/objectmodified.py

        # Member role must have view permission on /clients, to see the list.
        # This means within a client, perms granted on Member role are available
        # in clients not our own, allowing sideways entry if we're not careful.
        mp = portal.clients.manage_permission
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'Member', 'LabClerk', 'Analyst', 'Sampler', 'Preserver'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Member', 'Analyst', 'Sampler', 'Preserver'], 0)
        mp(permissions.ModifyPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Owner'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'Member', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'Owner'], 0)
        mp(ManageClients, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Owner'], 0)
        mp(AddAnalysisSpec, ['Manager', 'LabManager', 'Owner'], 0)
        portal.clients.reindexObject()

        for obj in portal.clients.objectValues():
            mp = obj.manage_permission
            mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'Member', 'LabClerk', 'Analyst', 'Sampler', 'Preserver'], 0)
            mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Member', 'Analyst', 'Sampler', 'Preserver'], 0)
            mp(permissions.ModifyPortalContent, ['Manager', 'LabManager', 'Owner'], 0)
            mp(AddSupplyOrder, ['Manager', 'LabManager', 'Owner'], 0)
            mp('Access contents information', ['Manager', 'LabManager', 'Member', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'Owner'], 0)
            obj.reindexObject()
            for contact in portal.clients.objectValues('Contact'):
                mp = contact.manage_permission
                mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Owner', 'Analyst', 'Sampler', 'Preserver'], 0)
                mp(permissions.ModifyPortalContent, ['Manager', 'LabManager', 'Owner'], 0)

        # /worksheets folder permissions
        mp = portal.worksheets.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'RegulatoryInspector'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'Analyst', 'RegulatoryInspector'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'Analyst', 'RegulatoryInspector'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.worksheets.reindexObject()

        # /batches folder permissions
        mp = portal.batches.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Authenticated', 'RegulatoryInspector'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'RegulatoryInspector'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Authenticated', 'RegulatoryInspector'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.batches.reindexObject()

        # /analysisrequests folder permissions
        mp = portal.analysisrequests.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'RegulatoryInspector'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'RegulatoryInspector'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'RegulatoryInspector'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.analysisrequests.reindexObject()

        # /referencesamples folder permissions
        mp = portal.referencesamples.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.referencesamples.reindexObject()

        # /samples folder permissions
        mp = portal.samples.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'RegulatoryInspector'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'RegulatoryInspector'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'RegulatoryInspector'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.samples.reindexObject()

        # /reports folder permissions
        mp = portal.reports.manage_permission
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'Member', 'LabClerk', 'Client'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Member', 'Client'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'Member', 'LabClerk', 'Owner', 'Client'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Owner', 'Member', 'Client'], 0)

        mp('ATContentTypes: Add Image', ['Manager', 'Labmanager', 'LabClerk', 'Member', 'Client'], 0)
        mp('ATContentTypes: Add File', ['Manager', 'Labmanager', 'LabClerk', 'Member', 'Client'], 0)
        portal.reports.reindexObject()

        # /invoices folder permissions
        mp = portal.invoices.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 1)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.View, ['Manager', 'LabManager'], 0)
        portal.invoices.reindexObject()

        # /pricelists folder permissions
        mp = portal.pricelists.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(ManagePricelists, ['Manager', 'LabManager', 'Owner'], 1)
        mp(permissions.ListFolderContents, ['Member'], 1)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.View, ['Manager', 'LabManager'], 0)
        portal.pricelists.reindexObject()

        # /methods folder permissions
        mp = portal.methods.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager'], 0)
        mp(permissions.ListFolderContents, ['Member', 'Authenticated', 'Anonymous'], 1)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager'], 0)
        mp(permissions.View, ['Manager', 'Member', 'Authenticated', 'Anonymous'], 1)
        mp('Access contents information', ['Manager', 'Member', 'Authenticated', 'Anonymous'], 1)
        portal.methods.reindexObject()

        try:
            # /supplyorders folder permissions
            mp = portal.supplyorders.manage_permission
            mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
            mp(ManagePricelists, ['Manager', 'LabManager', 'Owner'], 1)
            mp(permissions.ListFolderContents, ['Member'], 1)
            mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'Owner'], 0)
            mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
            mp(permissions.View, ['Manager', 'LabManager'], 0)
            portal.supplyorders.reindexObject()
        except:
            pass

        # Add Analysis Services View permission to Clients
        # (allow Clients to add attachments to Analysis Services from an AR)
        mp = portal.bika_setup.bika_analysisservices.manage_permission
        mp('Access contents information', ['Authenticated', 'Analyst', 'Client'], 1)
        mp(permissions.View, ['Authenticated', 'Analyst', 'Client'], 1)
        portal.bika_setup.bika_analysisservices.reindexObject()

        # Add Attachment Types View permission to Clients
        # (allow Clients to add attachments to Analysis Services from an AR)
        mp = portal.bika_setup.bika_attachmenttypes.manage_permission
        mp('Access contents information', ['Authenticated', 'Analyst', 'Client'], 1)
        mp(permissions.View, ['Authenticated', 'Analyst', 'Client'], 1)
        portal.bika_setup.bika_attachmenttypes.reindexObject()

        # /arimports folder permissions
        try:
            mp = portal.arimports.manage_permission
            mp(ManageARImport, ['Manager', ], 1)
            mp(permissions.ListFolderContents, ['Manager', 'Member',], 1)
            mp(permissions.AddPortalContent, ['Manager', ], 0)
            mp(permissions.DeleteObjects, ['Manager'], 0)
            mp(permissions.View, ['Manager', 'Member'], 0)
            portal.arimports.reindexObject()
        except:
            pass

    def setupVersioning(self, portal):
        portal_repository = getToolByName(portal, 'portal_repository')
        versionable_types = list(portal_repository.getVersionableContentTypes())

        for type_id in VERSIONABLE_TYPES:
            if type_id not in versionable_types:
                versionable_types.append(type_id)
                # Add default versioning policies to the versioned type
                for policy_id in DEFAULT_POLICIES:
                    portal_repository.addPolicyForContentType(type_id, policy_id)
        portal_repository.setVersionableContentTypes(versionable_types)

    def setupTopLevelFolders(self, context):
        workflow = getToolByName(context, "portal_workflow")
        obj_id = 'arimports'
        if obj_id in context.objectIds():
            obj = context._getOb(obj_id)
            try:
                workflow.doActionFor(obj, "hide")
            except:
                pass
            obj.setLayout('@@arimports')
            alsoProvides(obj, IARImportFolder)
            alsoProvides(obj, IHaveNoBreadCrumbs)


def setupVarious(context):
    """
    Final Bika import steps.
    """
    if context.readDataFile('bika.lims_various.txt') is None:
        return

    site = context.getSite()
    gen = BikaGenerator()
    gen.setupGroupsAndRoles(site)
    gen.setupPortalContent(site)
    gen.setupPermissions(site)
    gen.setupTopLevelFolders(site)
    try:
        from Products.CMFEditions.setuphandlers import DEFAULT_POLICIES
        # we're on plone < 4.1, configure versionable types manually
        gen.setupVersioning(site)
    except ImportError:
        # repositorytool.xml will be used
        pass

    # Plone's jQuery gets clobbered when jsregistry is loaded.
    setup = site.portal_setup
    setup.runImportStepFromProfile(
            'profile-plone.app.jquery:default', 'jsregistry')
    # setup.runImportStepFromProfile('profile-plone.app.jquerytools:default', 'jsregistry')

