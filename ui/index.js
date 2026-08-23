(function () {
  var Q = window.QwenPaw;
  if (!Q || !Q.host || !Q.host.React || !Q.registerRoutes) return;
  var React = Q.host.React, antd = Q.host.antd, h = React.createElement;
  function request(path, body) {
    return Q.host.fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) }).then(function (response) {
      return response.json().then(function (data) { if (!response.ok) throw new Error(data.detail || "操作失败"); return data; });
    });
  }
  function ServiceStudio() {
    var answerTextState = React.useState(""), answerText = answerTextState[0], setAnswerText = answerTextState[1];
    var answerState = React.useState(null), answerResult = answerState[0], setAnswerResult = answerState[1];
    var intentState = React.useState(null), intentResult = intentState[0], setIntentResult = intentState[1];
    var ticketState = React.useState({ customer_name: "", product: "", fault_type: "", description: "" });
    var ticketResultState = React.useState(null), ticketResult = ticketResultState[0], setTicketResult = ticketResultState[1];
    var ticketsState = React.useState([]), tickets = ticketsState[0], setTickets = ticketsState[1];
    var engineerState = React.useState(""), engineer = engineerState[0], setEngineer = engineerState[1];
    var reviewerState = React.useState(""), reviewer = reviewerState[0], setReviewer = reviewerState[1];
    var recordsTextState = React.useState(""), recordsText = recordsTextState[0], setRecordsText = recordsTextState[1];
    var knowledgeState = React.useState(null), knowledge = knowledgeState[0], setKnowledge = knowledgeState[1];
    var knowledgeReviewerState = React.useState(""), knowledgeReviewer = knowledgeReviewerState[0], setKnowledgeReviewer = knowledgeReviewerState[1];
    var loadingState = React.useState(false), loading = loadingState[0], setLoading = loadingState[1];
    var message = antd.App.useApp().message;
    function detect() {
      if (!answerText.trim()) { message.warning("请输入客户咨询文本"); return; }
      setLoading(true);
      request("/zhiyun-service-studio/intent/classify", { text: answerText }).then(setIntentResult)
        .catch(function (e) { message.error(e.message); }).finally(function () { setLoading(false); });
    }
    function runAnswer() {
      if (!answerText.trim()) { message.warning("请输入客户咨询文本"); return; }
      setLoading(true);
      request("/zhiyun-service-studio/answer", { text: answerText }).then(setAnswerResult)
        .catch(function (e) { message.error(e.message); }).finally(function () { setLoading(false); });
    }
    function updateTicket(name, value) { setTicketState(Object.assign({}, ticketState, {})); ticketState[name] = value; setTicketState(Object.assign({}, ticketState)); }
    function createTicket() {
      if (!ticketState.customer_name.trim() || !ticketState.description.trim()) { message.warning("请填写客户名称与问题描述"); return; }
      setLoading(true);
      request("/zhiyun-service-studio/tickets", ticketState).then(function (data) {
        setTicketResult(data);
        var best = data.recommendation.recommendations[0];
        setEngineer(best ? best.name : "");
        loadTickets();
      }).catch(function (e) { message.error(e.message); }).finally(function () { setLoading(false); });
    }
    function loadTickets() {
      return Q.host.fetch("/zhiyun-service-studio/tickets").then(function (response) { return response.json(); })
        .then(function (data) { setTickets(data.tickets || []); }).catch(function () {});
    }
    function decideTicket(action) {
      if (!reviewer.trim()) { message.warning("请输入审阅人"); return; }
      if (action === "accept" && !engineer.trim()) { message.warning("请确认分派工程师"); return; }
      request("/zhiyun-service-studio/tickets/" + ticketResult.id + "/reviews", { action: action, reviewer: reviewer, engineer: engineer }).then(function (data) {
        setTicketResult(data); message.success(action === "accept" ? "工单已接受并可派单" : "工单已驳回"); loadTickets();
      }).catch(function (e) { message.error(e.message); });
    }
    function buildKnowledge() {
      var records;
      try { records = JSON.parse(recordsText); } catch (err) { message.error("维修记录必须是JSON数组"); return; }
      if (!Array.isArray(records) || !records.length) { message.warning("请提供至少一条维修记录"); return; }
      setLoading(true);
      request("/zhiyun-service-studio/knowledge/artifacts", { records: records, title: "售后知识库" }).then(function (data) {
        setKnowledge(data); message.success("已提取 " + data.entries.length + " 条知识，等待审阅");
      }).catch(function (e) { message.error(e.message); }).finally(function () { setLoading(false); });
    }
    function decideKnowledge(action) {
      if (!knowledgeReviewer.trim()) { message.warning("请输入审阅人"); return; }
      request("/zhiyun-service-studio/knowledge/artifacts/" + knowledge.id + "/reviews", { action: action, reviewer: knowledgeReviewer }).then(function (data) {
        setKnowledge(data); message.success(action === "accept" ? "知识库已接受" : "知识库已驳回");
      }).catch(function (e) { message.error(e.message); });
    }
    var intentLabels = { order_status: "订单查询", after_sale: "售后报修", financial_support: "财务支持", return_exchange: "退换货", complaint: "投诉建议", product_info: "产品咨询", shipping: "物流配送", other: "其他" };
    var intents = [
      { key: "answer", label: "咨询应答与意图识别" },
      { key: "tickets", label: "售后工单管理" },
      { key: "knowledge", label: "知识库构建" }
    ];
    var activeState = React.useState("answer"), active = activeState[0], setActive = activeState[1];
    React.useEffect(function () { loadTickets(); }, []);
    return h("div", { style: { padding: 28, height: "100%", overflow: "auto", background: "#f7f8fa" } }, h("div", { style: { maxWidth: 1080, margin: "0 auto" } },
      h("h2", null, "智能售后服务中心"), h("p", { style: { color: "#667085" } }, "识别客户意图、知识化应答、售后工单路由与知识库构建。"),
      h(antd.Tabs, { activeKey: active, onChange: setActive, items: intents.map(function (item) {
        return { key: item.key, label: item.label, children: item.key === "answer" ? (
          h("div", null,
            h(antd.Input.TextArea, { value: answerText, rows: 5, onChange: function (e) { setAnswerText(e.target.value); }, placeholder: "粘贴真实客户咨询文本，如：我的电机有明显异响，订单A123456怎么处理？" }),
            h("div", { style: { display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" } },
              h(antd.Button, { type: "primary", loading: loading, onClick: runAnswer }, "生成应答"),
              h(antd.Button, { loading: loading, onClick: detect }, "识别意图")
            ),
            answerResult ? h(antd.Alert, { style: { marginTop: 16 }, type: "info", showIcon: true, message: "应答结果", description: h("div", null,
              h("p", null, answerResult.answer),
              h(antd.Tag, { color: "blue" }, answerResult.intent_label), h(antd.Tag, { color: "geekblue" }, "置信度 " + answerResult.confidence),
              answerResult.matched_faq ? h("p", { style: { color: "#667085" } }, "命中FAQ：" + answerResult.matched_faq) : null,
              answerResult.knowledge_hit ? h("p", { style: { color: "#52c41a" } }, "已引用历史维修知识") : null
            ) }) : null,
            intentResult ? h(antd.Card, { size: "small", title: "意图识别结果", style: { marginTop: 16 }, extra: h(antd.Tag, { color: intentResult.confidence > 0.6 ? "green" : "orange" }, "置信度 " + intentResult.confidence) },
              h(antd.Descriptions, { bordered: true, size: "small", column: 2, items: [
                { key: "intent", label: "意图", children: intentResult.intent_label },
                { key: "method", label: "方法", children: intentResult.method },
                { key: "keywords", label: "命中关键词", children: intentResult.matched_keywords.join("、") || "无" },
                { key: "entities", label: "实体", children: intentResult.entities.length ? intentResult.entities.map(function (e) { return e.type + ":" + e.value; }).join("、") : "无" }
              ] })
            ) : null
          )
        ) : item.key === "tickets" ? (
          h("div", null,
            h(antd.Divider, { plain: true }, "新建售后工单"),
            h("div", { style: { display: "grid", gridTemplateColumns: "repeat(2,minmax(240px,1fr))", gap: 12 } },
              [["customer_name", "客户名称"], ["product", "产品"], ["fault_type", "故障类型"]].map(function (field) {
                return h(antd.Input, { key: field[0], placeholder: field[1], value: ticketState[field[0]], onChange: function (e) { updateTicket(field[0], e.target.value); } });
              }),
              h(antd.Input, { placeholder: "问题说明（必填）", value: ticketState.description, onChange: function (e) { updateTicket("description", e.target.value); } })
            ),
            h(antd.Button, { type: "primary", loading: loading, style: { marginTop: 12 }, onClick: createTicket }, "生成工单并推荐工程师"),
            ticketResult ? h(antd.Card, { size: "small", title: "工单推荐", style: { marginTop: 16 }, extra: h(antd.Tag, { color: "orange" }, ticketResult.status) },
              h(antd.Alert, { type: "info", showIcon: true, message: "推荐团队：" + ticketResult.team, description: ticketResult.recommendation.recommendations.map(function (item) { return item.name + "（" + item.level + "，技能：" + (item.matched_skills.join("、") || "无匹配") + "）"; }).join("；") }),
              h("div", { style: { display: "flex", gap: 8, marginTop: 12 } },
                h(antd.Input, { value: engineer, onChange: function (e) { setEngineer(e.target.value); }, placeholder: "确认分派工程师", style: { width: 200 } }),
                h(antd.Input, { value: reviewer, onChange: function (e) { setReviewer(e.target.value); }, placeholder: "审阅人", style: { width: 160 } })
              ),
              h("div", { style: { marginTop: 8 } },
                h(antd.Button, { type: "primary", onClick: function () { decideTicket("accept"); } }, "接受并派单"),
                h(antd.Button, { style: { marginLeft: 8 }, danger: true, onClick: function () { decideTicket("reject"); } }, "驳回")
              )
            ) : null,
            h(antd.Divider, { plain: true }, "最近工单"),
            h(antd.Table, { size: "small", rowKey: "id", dataSource: tickets, pagination: { pageSize: 6 }, columns: [
              { title: "客户", dataIndex: "customer_name" }, { title: "问题", dataIndex: "description", ellipsis: true },
              { title: "团队", dataIndex: "team" }, { title: "工程师", dataIndex: "recommended_engineer" },
              { title: "状态", dataIndex: "status", render: function (v) { return h(antd.Tag, { color: v === "accepted" ? "green" : v === "rejected" ? "red" : "orange" }, v); } }
            ] })
          )
        ) : (
          h("div", null,
            h(antd.Alert, { type: "info", showIcon: true, message: "从真实维修记录提取知识", description: "粘贴JSON数组，每项含 fault_type(故障)、cause(原因)、solution(方案)、product(产品)。" }),
            h(antd.Input.TextArea, { style: { marginTop: 12 }, value: recordsText, rows: 8, onChange: function (e) { setRecordsText(e.target.value); }, placeholder: '[{"fault_type":"电机异响","cause":"轴承磨损","solution":"更换轴承并重新装配","product":"电机"}]' }),
            h(antd.Button, { type: "primary", loading: loading, style: { marginTop: 12 }, onClick: buildKnowledge }, "构建并审阅知识库"),
            knowledge ? h(antd.Card, { size: "small", title: "知识库（" + knowledge.entries.length + " 条）", style: { marginTop: 16 }, extra: h(antd.Tag, { color: knowledge.status === "accepted" ? "green" : "orange" }, knowledge.status) },
              h(antd.List, { size: "small", dataSource: knowledge.entries, renderItem: function (item) {
                return h(antd.List.Item, null, h("div", null,
                  h("strong", null, item.problem),
                  h("div", { style: { color: "#667085" } }, item.cause ? "原因：" + item.cause : "", item.solution ? "；方案：" + item.solution : ""),
                  h("div", null, item.tags.map(function (tag) { return h(antd.Tag, { key: tag }, tag); }))
                ));
              } }),
              h("div", { style: { display: "flex", gap: 8, marginTop: 12 } },
                h(antd.Input, { value: knowledgeReviewer, onChange: function (e) { setKnowledgeReviewer(e.target.value); }, placeholder: "审阅人", style: { width: 180 } }),
                h(antd.Button, { type: "primary", onClick: function () { decideKnowledge("accept"); } }, "接受"),
                h(antd.Button, { danger: true, onClick: function () { decideKnowledge("reject"); } }, "驳回"),
                h(antd.Button, { disabled: knowledge.status !== "accepted", onClick: function () { window.open("/zhiyun-service-studio/knowledge/artifacts/" + knowledge.id + "/export", "_blank"); } }, "导出")
              )
            ) : null
          )
        )};
      }) }
    )));
  }
  Q.registerRoutes("zhiyun-service-studio", [{ path: "/apps/zhiyun-service-studio", component: ServiceStudio, label: "智能售后服务中心", icon: "🎧", priority: 84 }]);
})();
