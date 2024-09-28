# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# Copyright 2019 信莱德软件
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import base64
import json
from werkzeug import exceptions
from werkzeug.urls import url_decode,url_unquote_plus,url_quote
from odoo.tools.safe_eval import safe_eval, time

from odoo.http import route, request, serialize_exception, content_disposition
from odoo.tools import html_escape
from odoo.addons.web.controllers import report

import logging
_logger = logging.getLogger(__name__)

html_template='''
<!DOCTYPE html>
<html>
<head>
    <title>%s</title>
    <style>
        .pdf-container {
            width: 100%%;
            height: 100vh; /* 使用视口高度作为高度 */
        }
    </style>
</head>
<body>
    <embed class="pdf-container" src="data:application/pdf;base64,%s" type="application/pdf" title="%s">
</body>
</html>
'''


class ReportController(report.ReportController):
    TYPES_MAPPING = {
        'doc': 'application/vnd.ms-word',
        'html': 'text/html',
        'odt': 'application/vnd.oasis.opendocument.text',
        'pdf': 'application/pdf',
        'sxw': 'application/vnd.sun.xml.writer',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }

    @route( [
            "/report/<converter>/<reportname>",
            "/report/<converter>/<reportname>/<docids>",
            "/report/<converter>/<reportname>/<docids>/<filename>",
        ],
        type="http",
        auth="user",
        website=True,)
    def report_routes(
        self, reportname, docids=None, converter=None, options=None, **kwargs
    ):
        if converter == "docx":
            docids = [int(_id) for _id in (docids or "").split(",")]
            data = {**json.loads(options or "{}"), **kwargs}
            context = dict(request.env.context)
            if "context" in data:
                data["context"] = json.loads(data["context"] or "{}")
                # Ignore 'lang' here, because the context in data is the one from the
                # webclient *but* if the user explicitely wants to change the lang, this
                # mechanism overwrites it.
                if "lang" in data["context"]:
                    del data["context"]["lang"]
                context.update(data["context"])
            ir_action = request.env['ir.actions.report']
            action_docx_report = ir_action.get_from_report_name(
                reportname, "docx").with_context(context)
            if not action_docx_report:
                raise exceptions.HTTPException(
                    description='Docx action report not found for report_name '
                                '%s' % reportname)
            pdf, filetype = action_docx_report.render_docx(docids, data)
            filename = action_docx_report.gen_report_download_filename(
                docids, data)
            if not filename.endswith(filetype):
                filename = "{}.{}".format(filename, filetype)

            if filetype == 'docx':
                headers = [
                    ("Content-Disposition", "%s" % content_disposition(filename))
                ]
            else:
                headers = [
                    ("Content-Type", "application/pdf"),
                    ("Content-Length", len(pdf)),
                    ("Content-Disposition", 'inline; filename="%s"' % url_quote(filename))
                ]
            return request.make_response(
                pdf,
                headers
            )


        elif converter =='pdf':
            report_obj = request.env["ir.actions.report"]
            report = report_obj._get_report_from_name(reportname)
            context = dict(request.env.context)

            # Options
            if kwargs.get("options"):
                data_options = kwargs.pop("options")
                kwargs.update(json.loads(url_unquote_plus(data_options)))

            # Context
            data_context = kwargs.get("context")
            if data_context:
                context.update(json.loads(url_unquote_plus(data_context)))

            # Set allowed companies if provided explicitly
            if kwargs.get("cid"):
                allowed_company_ids = [int(i) for i in kwargs.get("cid").split(",")]
                context.update(allowed_company_ids=allowed_company_ids)

            # Update request context
            request.env.context = context

            # Doc IDs
            if docids:
                docids = [int(i) for i in docids.split(",")]

                # Ensure user has access to the documents
                records = request.env[report.model].browse(docids)
                records.check_access_rule("read")

            pdf = report_obj.with_context(**context)._render_qweb_pdf(
                reportname, docids, data=kwargs
            )[0]

            return request.make_response(
                pdf,
                headers=[
                    ("Content-Type", "application/pdf"),
                    ("Content-Length", len(pdf)),
                    ("Content-Disposition", 'inline; filename="%s"' % content_disposition(report.name+'.pdf')),
                ],
            )
        else:
            return super().report_routes(
                reportname,
                docids=docids,
                converter=converter,
                options=options,
                **kwargs,
            )

    @route()
    def report_download(self, data, context=None, token=None):
        """This function is used by 'qwebactionmanager.js' in order to trigger
        the download of a docx/controller report.

        :param data: a javascript array JSON.stringified containg report
        internal url ([0]) and type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = json.loads(data)
        url, report_type = requestcontent[0], requestcontent[1]
        if 'docx' not in report_type:
            return super().report_download(data, context, token)
        try:
            reportname = url.split('/report/docx/')[1].split('?')[0]
            docids = None
            if '/' in reportname:
                reportname, docids = reportname.split('/')

            if docids:
                # Generic report:
                response = self.report_routes(
                    reportname, docids=docids, converter='docx')
            else:
                # Particular report:
                # decoding the args represented in JSON
                data = list(url_decode(url.split('?')[1]).items())
                response = self.report_routes(
                    reportname, converter='docx', **dict(data))
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))








