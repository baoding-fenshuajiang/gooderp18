/** @odoo-module */

import {download} from "@web/core/network/download";
import {registry} from "@web/core/registry";
import {WARNING_MESSAGE, WKHTMLTOPDF_MESSAGES, _getReportUrl} from "./tools.esm";

function getReportUrl({report_name, context, data}, env) {
    let url = `/report/docx/${report_name}`;
    const actionContext = context || {};
    if (data && JSON.stringify(data) !== "{}") {
        const encodedOptions = encodeURIComponent(JSON.stringify(data));
        const encodedContext = encodeURIComponent(JSON.stringify(actionContext));
        return `${url}?options=${encodedOptions}&context=${encodedContext}`;
    }
    if (actionContext.active_ids) {
        url += `/${actionContext.active_ids.join(",")}`;
    }
    const userContext = encodeURIComponent(JSON.stringify(env.services.user.context));
    return `${url}?context=${userContext}`;
}
async function triggerDownload(action, {onClose}, env) {
    env.services.ui.block();
    const data = JSON.stringify([getReportUrl(action, env), action.report_type]);
    const context = JSON.stringify(env.services.user.context);
    try {
        await download({url: "/report/download", data: {data, context}});
    } finally {
        env.services.ui.unblock();
    }
    if (action.close_on_report_download) {
        return env.services.action.doAction(
            {type: "ir.actions.act_window_close"},
            {onClose}
        );
    }
    if (onClose) {
        onClose();
    }
}
registry
    .category("ir.actions.report handlers")
    .add("docx_handler", async function (action, options, env) {
        console.log('docx')
        if (action.report_type === "docx") {
                console.log('docx')
                const url = _getReportUrl(action, "docx", env);
                // AAB: this check should be done in get_file service directly,
                // should not be the concern of the caller (and that way, get_file
                // could return a deferred)
                if (!window.open(url)) {
                    env.services.notification.add(WARNING_MESSAGE, {
                        type: "warning",
                    });
                }
            return true;
        }
        return false;
    });

/* Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
 * Copyright 2019 信莱德软件 <www.zhsunlight.cn>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
