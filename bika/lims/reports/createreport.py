from Products.CMFPlone.utils import _createObjectByType
from bika.lims.utils import tmpID, logged_in_client
from zExceptions import BadRequest
from zope.interface import alsoProvides
from bika.lims.reports.interfaces import *


class CreateReport(object):
    """docstring for CreateReport"""

    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def next_report_id(self, report_type):
        prefix = report_type.split("_")[-1]
        existing = [x for x in self.context.objectValues()
                    if x.id.find(prefix) > -1]
        return '%s-%s' % (prefix, len(existing) + 1)

    def __call__(self):
        """this function provides the default values for the queries used
        to retrieve and format report data.

        1) 'query' is the QueryField attached to the reportcollection object.
           we set defaults here, which the user can change, but probably
           will not. We should include all valid indexes here, the user can
           remove what they do not need.
        2) 'base_query' this is a simple object attribute, consisting of
           a dictionary of indexes and values which will be updated into the
           query field's value after it is parsed.
        """
        if 'report' not in self.request:
            raise BadRequest("No report was specified in request!")
        report_type = self.request['report']
        next_id = self.next_report_id(report_type)
        obj = _createObjectByType('ReportCollection', self.context, next_id)
        obj.setTitle(next_id)
        obj.unmarkCreationFlag()

        if report_type == 'productivity_dailysamplesreceived':
            alsoProvides(obj, IDailySamplesReceived)
            obj.base_query = {'portal_type': 'Sample'}
            obj.Schema().getField('query').set(obj, [
                {'i': 'DateReceived',
                 'o': 'plone.app.querystring.operation.date.today',
                 'v': ['', '']}
            ])

        elif report_type == 'productivity_samplesreceivedvsreported':
            alsoProvides(obj, ISamplesReceivedVsReported)
            obj.base_query = {'portal_type': 'Sample'}
            obj.Schema().getField('query').set(obj, [
                {'i': 'DateReceived',
                 'o': 'plone.app.querystring.operation.date.today',
                 'v': ['', '']}
            ])
        elif report_type == 'productivity_analysesperservice':
            alsoProvides(obj, IAnalysesPerService)
            obj.base_query = {'portal_type': 'Analysis'}
            obj.Schema().getField('query').set(obj, [
                {'i': 'created',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'DatePublished',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'cancellation_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'worksheetanalysis_review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'productivity_analysespersampletype':
            alsoProvides(obj, IAnalysesPerSampleType)
            obj.base_query = {'portal_type': 'Analysis'}
            obj.Schema().getField('query').set(obj, [
                {'i': 'created',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'cancellation_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'worksheetanalysis_review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'productivity_analysesperclient':
            alsoProvides(obj, IAnalysesPerClient)
            obj.base_query = {'portal_type': 'Analysis'}
            obj.Schema().getField('query').set(obj, [
                {'i': 'created',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'cancellation_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'worksheetanalysis_review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'productivity_analysestats':
            alsoProvides(obj, IAnalysesStats)
            obj.base_query = {'portal_type': 'Analysis'}
            obj.Schema().getField('query').set(obj, [
                {'i': 'ClientTitle',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'DateReceived',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'worksheetanalysis_review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'productivity_analysestats_overtime':
            alsoProvides(obj, IAnalysesStatsOverTime)
            obj.Schema().getField('query').set(obj, [
                {'i': 'AnalysisService',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'Analyst',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'InstrumentTitle',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'DateReceived',
                 'o': 'plone.app.querystring.operation.date.today'}
            ])
        elif report_type == 'productivity_analysesperdepartment':
            alsoProvides(obj, IAnalysesPerDepartment)
            obj.Schema().getField('query').set(obj, [
                {'i': 'created',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'productivity_analysesperformedpertotal':
            alsoProvides(obj, IAnalysesPerformedPerTotal)
            obj.Schema().getField('query').set(obj, [
                {'i': 'created',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'productivity_analysesattachments':
            alsoProvides(obj, IAnalysesAttachments)
            obj.Schema().getField('query').set(obj, [
                {'i': 'ClientTitle',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'created',
                 'o': 'plone.app.querystring.operation.date.today'}
            ])
        elif report_type == 'productivity_dataentrydaybook':
            alsoProvides(obj, IDataEntryDayBook)
            obj.Schema().getField('query').set(obj, [
                {'i': 'created',
                 'o': 'plone.app.querystring.operation.date.today'}
            ])
        # Specification to be added in qualitycontrol_analysesoutofrange
        elif report_type == 'qualitycontrol_analysesoutofrange':
            alsoProvides(obj, IAnalysesOutOfRange)
            obj.Schema().getField('query').set(obj, [
                {'i': 'DateReceived',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'cancellation_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'worksheetanalysis_review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'qualitycontrol_analysesrepeated':
            alsoProvides(obj, IAnalysesRepeated)
            obj.Schema().getField('query').set(obj, [
                {'i': 'DateReceived',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'cancellation_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'worksheetanalysis_review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'qualitycontrol_resultspersamplepoint':
            alsoProvides(obj, IResultsPerSamplePoint)
            obj.Schema().getField('query').set(obj, [
                {'i': 'ClientTitle',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'SamplePointTitle',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'SampleTypeTitle',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'AnalysisService',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'DateSampled',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'worksheetanalysis_review_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        # incomplete information about below 2 reports
        elif report_type == 'qualitycontrol_referenceanalysisqc':
            alsoProvides(obj, IReferenceAnalysisQC)
            obj.Schema().getField('query').set(obj, [
                # {'i': 'AnalysisService',
                # 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'qualitycontrol_duplicateanalysisqc':
            alsoProvides(obj, IDuplicateAnalysisQC)
            obj.Schema().getField('query').set(obj, [
                # {'i': 'created',
                # 'o': 'plone.app.querystring.operation.date.today'}
            ])
        elif report_type == 'administration_arsnotinvoiced':
            alsoProvides(obj, IArsNotInvoiced)
            obj.Schema().getField('query').set(obj, [
                {'i': 'DatePublished',
                 'o': 'plone.app.querystring.operation.date.today'},
                {'i': 'review_state',
                 'o': 'plone.app.querystring.operation.selection.is'},
                {'i': 'cancellation_state',
                 'o': 'plone.app.querystring.operation.selection.is'}
            ])
        elif report_type == 'administration_userhistory':
            alsoProvides(obj, IUserHistory)
            obj.Schema().getField('query').set(obj, [
                {'i': 'modified',
                 'o': 'plone.app.querystring.operation.date.today'}
            ])

        # Redirect to the edit page, to allow the user to complete parameters
        self.request.response.redirect(obj.absolute_url() + '/edit')
