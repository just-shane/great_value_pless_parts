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

var MACHINE_LABELS = {
  mill: "CNC Mill",
  lathe: "CNC Lathe (Turning)",
  swiss: "Swiss / Screw Machine",
};

function setText(id, text) {
  var el = document.getElementById(id);
  if (el) el.textContent = text;
}

function humanize(token) {
  return String(token).replace(/_/g, " ");
}

function renderQuote(q) {
  document.getElementById("empty-state").hidden = true;
  document.getElementById("quote").hidden = false;

  setText("unit-price", money(q.unit_price, q.currency));
  setText("quantity", q.quantity);
  setText("total-price", money(q.total_price, q.currency));
  setText("cycle-time", (Number(q.estimated_cycle_time_sec || 0) / 60).toFixed(1) + " min");
  setText("setup-time", Number(q.setup_time_min || 0).toFixed(0) + " min");
  setText("lead-time", q.lead_time_days + " days");
  setText("part-name", q.part_name);
  setText("material", q.material);
  setText("machine", MACHINE_LABELS[q.machine_type] || q.machine_type);

  // Confidence badge
  var badge = document.getElementById("confidence");
  var conf = (q.confidence || "").toLowerCase();
  badge.textContent = conf ? conf + " confidence" : "—";
  badge.className = "badge badge--" + (conf || "medium");

  // Quantity price breaks (highlight the requested qty)
  var breaksBody = document.getElementById("price-breaks");
  breaksBody.innerHTML = "";
  (q.price_breaks || []).forEach(function (b) {
    var tr = document.createElement("tr");
    if (b.qty === q.quantity) tr.className = "is-current";
    var qtyCell = document.createElement("td");
    qtyCell.textContent = b.qty;
    var priceCell = document.createElement("td");
    priceCell.className = "br-price";
    priceCell.textContent = money(b.unit_price, q.currency);
    tr.appendChild(qtyCell);
    tr.appendChild(priceCell);
    breaksBody.appendChild(tr);
  });

  // Cost breakdown
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

  // Flags (chips)
  var flags = document.getElementById("flags");
  flags.innerHTML = "";
  (q.flags || []).forEach(function (f) {
    var li = document.createElement("li");
    li.className = "flag";
    li.textContent = humanize(f);
    flags.appendChild(li);
  });

  // Notes
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
