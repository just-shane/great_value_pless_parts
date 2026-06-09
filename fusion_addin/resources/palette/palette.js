/* Palette UI logic for Great Value Pless Parts.
 *
 * Two-way bridge with the Fusion add-in:
 *   Python -> JS : palette.sendInfoToHTML(action, data)
 *                  -> window.fusionJavaScriptHandler.handle(action, data)
 *   JS -> Python : adsk.fusionSendData(action, data)
 *                  -> palette.incomingFromHTML event
 */

function money(value, currency) {
  var n = Number(value || 0);
  var prefix = !currency || currency === "USD" ? "$" : currency + " ";
  return prefix + n.toFixed(2);
}

var PROCESS_LABELS = {
  cnc_milling: "CNC Milling",
  cnc_turning: "CNC Turning",
};

function setText(id, text) {
  var el = document.getElementById(id);
  if (el) el.textContent = text;
}

function renderQuote(q) {
  document.getElementById("empty-state").hidden = true;
  document.getElementById("quote").hidden = false;

  setText("unit-price", money(q.unit_price, q.currency));
  setText("quantity", q.quantity);
  setText("total-price", money(q.total_price, q.currency));
  setText("lead-time", q.lead_time_days + " days");
  setText("part-name", q.part_name);
  setText("material", q.material);
  setText("process", PROCESS_LABELS[q.process] || q.process);

  var tbody = document.getElementById("line-items");
  tbody.innerHTML = "";
  (q.line_items || []).forEach(function (li) {
    var tr = document.createElement("tr");

    var labelCell = document.createElement("td");
    labelCell.className = "li-label";
    labelCell.appendChild(document.createTextNode(li.label));
    if (li.detail) {
      var detail = document.createElement("div");
      detail.className = "li-detail";
      detail.textContent = li.detail;
      labelCell.appendChild(detail);
    }

    var amountCell = document.createElement("td");
    amountCell.className = "li-amount";
    amountCell.textContent = money(li.amount, q.currency);

    tr.appendChild(labelCell);
    tr.appendChild(amountCell);
    tbody.appendChild(tr);
  });

  var notes = document.getElementById("notes");
  notes.innerHTML = "";
  (q.notes || []).forEach(function (note) {
    var li = document.createElement("li");
    li.textContent = note;
    notes.appendChild(li);
  });

  setText("disclaimer", q.disclaimer || "");
}

// Python -> JS entry point.
window.fusionJavaScriptHandler = {
  handle: function (action, data) {
    try {
      if (action === "quote") {
        renderQuote(JSON.parse(data));
      }
      return "OK";
    } catch (e) {
      return "FAILED: " + e;
    }
  },
};

// JS -> Python helper.
function sendToFusion(action, payload) {
  if (window.adsk && window.adsk.fusionSendData) {
    return window.adsk.fusionSendData(action, JSON.stringify(payload || {}));
  }
}

// Let Python know the page is ready so it can (re)send the latest quote.
window.addEventListener("DOMContentLoaded", function () {
  sendToFusion("ready", {});
});
