from Acquisition import aq_inner
from Acquisition import aq_parent
from Products.CMFCore.utils import getToolByName
from bika.lims.permissions import AddMultifile
from Products.Archetypes.BaseContent import BaseContent
from bika.lims.upgrade import stub
from bika.lims import logger

def upgrade(tool):
    """Upgrade step required for Bika LIMS 3.1.9
    """
    portal = aq_parent(aq_inner(tool))
    setup = portal.portal_setup

    # Friendly message
    qi = portal.portal_quickinstaller
    ufrom = qi.upgradeInfo('bika.lims')['installedVersion']
    logger.info("Upgrading Bika LIMS: %s -> %s" % (ufrom, '319'))

    # Updated profile steps
    # important info about upgrade steps in
    # http://stackoverflow.com/questions/7821498/is-there-a-good-reference-list-for-the-names-of-the-genericsetup-import-steps
    setup.runImportStepFromProfile('profile-bika.lims:default', 'typeinfo')
    setup.runImportStepFromProfile('profile-bika.lims:default', 'jsregistry')
    setup.runImportStepFromProfile('profile-bika.lims:default', 'cssregistry')
    setup.runImportStepFromProfile('profile-bika.lims:default', 'workflow-csv')
    setup.runImportStepFromProfile('profile-bika.lims:default', 'catalog')
    setup.runImportStepFromProfile('profile-bika.lims:default', 'skins')

    # Update workflow permissions
    wf = getToolByName(portal, 'portal_workflow')
    wf.updateRoleMappings()

    # Migrations
    port_indexes_to_portal_catalog(portal)


    return True


def port_indexes_to_portal_catalog(portal):
    at = getToolByName(portal, 'archetype_tool')

    #https://jira.bikalabs.com/browse/LIMS-1851
    if "bika_catalog" in portal:
        portal.manage_delObjects(['bika_catalog'])

    #https://jira.bikalabs.com/browse/LIMS-1914
    if "bika_analysis_catalog" in portal:
        portal.manage_delObjects(['bika_analysis_catalog'])

    # These are moved to portal_catalog.
    at.setCatalogsByType('Analysis', ['portal_catalog', ])
    at.setCatalogsByType('AnalysisRequest', ['portal_catalog', ])
    at.setCatalogsByType('Batch', ['portal_catalog', ])
    at.setCatalogsByType('Sample', ['portal_catalog', ])
    at.setCatalogsByType('SamplePartition', ['portal_catalog', ])
    at.setCatalogsByType('Worksheet', ['portal_catalog', ])
    at.setCatalogsByType('DuplicateAnalysis', ['portal_catalog', ])
    at.setCatalogsByType('ReferenceAnalysis', ['portal_catalog', ])
    at.setCatalogsByType('Report', ['portal_catalog', ])
    at.setCatalogsByType('ReferenceSample', ['portal_catalog', ])

