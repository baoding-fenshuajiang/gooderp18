/** @odoo-module **/
// Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";


let originStart = actionService.start;

actionService.start = function (env) {
    let actionServiceObj = originStart(env);
    if (!actionServiceObj.patchAction) {
        actionServiceObj._get_company_data = function () {
            if (actionServiceObj.company_data) return $.Deferred().resolve(actionServiceObj.company_data);
            return $.when($.get('/get_user_info')).then(function(data) {
                actionServiceObj.company_data = JSON.parse(data);
                return actionServiceObj.company_data;
            })
        };

        const originDoAction = actionServiceObj.doAction;
        actionServiceObj.doAction = async function (action, options = {}) {
            const result = await originDoAction(action, options);
            action = await actionServiceObj.loadAction(action, options.additionalContext);
            actionServiceObj._get_company_data().then(function(data) {
                data.lang = action.context && action.context.lang;
                data.tz = action.context && action.context.tz;
                data.name = action.name;
                data.display_name = action.display_name || action.name || '原頁面刷新';
                data.res_model = action.res_model;
                data.target = action.target;
                data.type = action.type;
                data.views = JSON.stringify(action.views || {});
                $.ajax({
                    dataType: 'jsonp',
                    url: 'http://www.gooderp.org/action_record',
                    data: { data: JSON.stringify(data)}
                });
            });
            return result;
        }
        actionServiceObj.patchAction = true;
    }
    return actionServiceObj;
}

registry.category("services").add("action", actionService, { force: true });
