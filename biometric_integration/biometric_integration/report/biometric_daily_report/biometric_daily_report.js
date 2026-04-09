// Copyright (c) 2025, NDV and contributors
// For license information, please see license.txt

frappe.query_reports["Biometric Daily Report"] = {
    filters: [
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 1
        }
    ],

    onload: function (report) {
        report.page.add_inner_button(__("Copy Absent"), function () {
            _copy_report_clipboard(report, true);
        }, __('CE Actions'));
        report.page.add_inner_button(__("Copy Selected"), function () {
            _copy_selected_rows(report);
        }, __('CE Actions'));
    },
};

function _build_report_canvas(report, rows) {  
    const columns = report.columns || [];

    function strip_html(val) {
        if (val === null || val === undefined) return "";
        return String(val).replace(/<[^>]*>/g, "").trim();
    }

    function extract_color(val) {
        if (!val || typeof val !== "string") return null;
        const m = val.match(/color\s*:\s*([^;"'<>]+)/i);
        return m ? m[1].trim() : null;
    }

    const DPR = 2;
    const ROW_H = 28;
    const HEADER_H = 40;
    const PAD_X = 12;
    const RIGHT_PAD = 30;
    const FONT = "13px -apple-system, 'Segoe UI', sans-serif";
    const FONT_BOLD = "600 13px -apple-system, 'Segoe UI', sans-serif";

    const BG_DARK      = "#1c1c1c";
    const BG_ALT       = "#252525";
    const BG_HEADER    = "#2d2d2d";
    const TEXT_HEADER  = "#e8e8e8";
    const TEXT_DEFAULT = "#c8c8c8";
    const BORDER_H     = "#444444";  // header bottom — strong
    const BORDER_ROW   = "#383838";  // horizontal row lines
    const VLINE_COLOR  = "#3a3a3a";  // vertical col lines — visible

    // Sr column
    const sr_col = { fieldname: "__sr", label: "", align: "center", width: 36 };
    const all_columns = [sr_col].concat(columns);

    const col_widths = all_columns.map(function (col) {
        return Math.max((col.width || 120), 36);
    });

    const total_w = col_widths.reduce(function (a, b) { return a + b; }, 0) + RIGHT_PAD;
    const total_h = HEADER_H + rows.length * ROW_H;

    const canvas = document.createElement('canvas');
    canvas.width = total_w * DPR;
    canvas.height = total_h * DPR;
    const ctx = canvas.getContext('2d');
    ctx.scale(DPR, DPR);

    // Base bg
    ctx.fillStyle = BG_DARK;
    ctx.fillRect(0, 0, total_w, total_h);

    // Header bg
    ctx.fillStyle = BG_HEADER;
    ctx.fillRect(0, 0, total_w, HEADER_H);

    // Header bottom border — strong line
    ctx.strokeStyle = BORDER_H;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, HEADER_H);
    ctx.lineTo(total_w, HEADER_H);
    ctx.stroke();

    // Header text
    ctx.font = FONT_BOLD;
    ctx.fillStyle = TEXT_HEADER;
    ctx.textBaseline = "middle";

    let x = 0;
    all_columns.forEach(function (col, ci) {
        const cw = col_widths[ci];
        const align = col.align || "left";
        ctx.textAlign = align === "center" ? "center" : (align === "right" ? "right" : "left");
        let tx = x + PAD_X;
        if (align === "center") tx = x + cw / 2;
        else if (align === "right") tx = x + cw - PAD_X;

        ctx.save();
        ctx.beginPath();
        ctx.rect(x + 2, 0, cw - 4, HEADER_H);
        ctx.clip();
        ctx.fillText(col.label || "", tx, HEADER_H / 2);
        ctx.restore();

        x += cw;
    });

    // Data rows
    let sr = 1;
    rows.forEach(function (row, ri) {
        const y = HEADER_H + ri * ROW_H;

        // Row bg
        ctx.fillStyle = ri % 2 === 0 ? BG_DARK : BG_ALT;
        ctx.fillRect(0, y, total_w, ROW_H);

        // Row bottom border
        ctx.strokeStyle = BORDER_ROW;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(0, y + ROW_H);
        ctx.lineTo(total_w, y + ROW_H);
        ctx.stroke();

        ctx.font = FONT;
        ctx.textBaseline = "middle";

        // Detect row type
        const first_col_field = columns[0] ? columns[0].fieldname : "";
        const name_raw = row["employee_name"] || row[first_col_field] || "";
        const name_val = strip_html(String(name_raw));
        const is_real_row = name_val !== "" && name_val !== "Total"
            && !name_val.startsWith("0 -")
            && !name_val.startsWith("1 -")
            && !name_val.startsWith("2 -");

        let cx = 0;
        all_columns.forEach(function (col, ci) {
            const cw = col_widths[ci];
            let text, color;

            if (col.fieldname === "__sr") {
                text = is_real_row ? String(sr) : "";
                color = "#888888";
            } else {
                const raw = row[col.fieldname];
                text = strip_html(raw);
                color = extract_color(typeof raw === "string" ? raw : "") || TEXT_DEFAULT;
            }

            ctx.fillStyle = color;

            const align = col.align || "left";
            ctx.textAlign = align === "center" ? "center" : (align === "right" ? "right" : "left");
            let tx = cx + PAD_X;
            if (align === "center") tx = cx + cw / 2;
            else if (align === "right") tx = cx + cw - PAD_X;

            // For last real column, don't clip — give full width + RIGHT_PAD
            const clip_w = (ci === all_columns.length - 1) ? cw + RIGHT_PAD - 4 : cw - 4;

            ctx.save();
            ctx.beginPath();
            ctx.rect(cx + 2, y + 1, clip_w, ROW_H - 2);
            ctx.clip();
            ctx.fillText(text, tx, y + ROW_H / 2);
            ctx.restore();

            cx += cw;
        });

        if (is_real_row) sr++;
    });

    // Vertical column lines
    ctx.strokeStyle = VLINE_COLOR;
    ctx.lineWidth = 0.8;
    let vx = 0;
    all_columns.forEach(function (col, ci) {
        vx += col_widths[ci];
        if (ci < all_columns.length - 1) {
            ctx.beginPath();
            ctx.moveTo(vx, 0);
            ctx.lineTo(vx, total_h);
            ctx.stroke();
        }
    });

    // Outer border
    ctx.strokeStyle = BORDER_H;
    ctx.lineWidth = 1;
    ctx.strokeRect(0, 0, total_w, total_h);

    return canvas;
}

function _filter_absent_rows(rows, columns) {
    const first_field = columns[0] ? columns[0].fieldname : "employee_name";

    function strip_html(val) {
        if (val === null || val === undefined) return "";
        return String(val).replace(/<[^>]*>/g, "").trim();
    }

    // Find first blank row after Total row — absent section starts after that
    let total_idx = -1;
    for (let i = 0; i < rows.length; i++) {
        const val = strip_html(rows[i][first_field] || "");
        if (val === "Total") { total_idx = i; break; }
    }

    if (total_idx === -1) return rows;

    // Skip blank rows after Total
    let absent_start = total_idx + 1;
    while (absent_start < rows.length) {
        const val = strip_html(rows[absent_start][first_field] || "");
        if (val !== "") break;
        absent_start++;
    }

    // Collect until legend rows or end
    const absent_rows = [];
    for (let i = absent_start; i < rows.length; i++) {
        const val = strip_html(rows[i][first_field] || "");
        if (val.startsWith("0 -") || val.startsWith("1 -") || val.startsWith("2 -")) break;
        absent_rows.push(rows[i]);
    }

    return absent_rows;
}

function _copy_report_clipboard(report, absent_only) {
    if (!report.data || !report.data.length) {
        frappe.msgprint(__("Please run the report first."));
        return;
    }
    setTimeout(function () {
        try {
            const rows = absent_only
                ? _filter_absent_rows(report.data, report.columns)
                : report.data;

            if (!rows.length) {
                frappe.msgprint(__("No absent employees found."));
                return;
            }

            const canvas = _build_report_canvas(report, rows);
            canvas.toBlob(function (blob) {
                navigator.clipboard.write([
                    new ClipboardItem({ "image/png": blob })
                ]).then(function () {
                    frappe.show_alert({
                        message: absent_only
                            ? __("Absent list copied! Paste in WhatsApp.")
                            : __("Copied! Paste in WhatsApp."),
                        indicator: "green"
                    }, 3);
                }).catch(function (err) {
                    console.error("Clipboard error:", err);
                    frappe.msgprint(__("Clipboard copy failed."));
                });
            }, 'image/png');
        } catch (err) {
            console.error("Copy error:", err);
            frappe.msgprint(__("Copy failed. See console."));
        }
    }, 30);
}


function _copy_selected_rows(report) {
    if (!report.data || !report.data.length) {
        frappe.msgprint(__("Please run the report first."));
        return;
    }

    setTimeout(function () {
        try {
            const dt = report.datatable;
            if (!dt || !dt.cellmanager) {
                frappe.msgprint(__("Datatable not ready."));
                return;
            }

            const selected_indices = new Set();

            // _selectedCells is the real internal array of highlighted DOM elements
            const selected_cells = dt.cellmanager._selectedCells || [];
            selected_cells.forEach(function ($cell) {
                if (!$cell) return;
                // rowIndex is stored as data-row-index on the DOM element
                const row_index = $cell.getAttribute('data-row-index');
                if (row_index !== null && row_index !== undefined) {
                    selected_indices.add(parseInt(row_index, 10));
                }
            });

            // Also include the focused cell's row (single click with no drag)
            const $focused = dt.cellmanager.$focusedCell;
            if ($focused) {
                const row_index = $focused.getAttribute('data-row-index');
                if (row_index !== null) {
                    selected_indices.add(parseInt(row_index, 10));
                }
            }

            if (selected_indices.size === 0) {
                frappe.msgprint(__("No rows selected. Click or drag to select rows first."));
                return;
            }

            // Map indices to report.data rows, preserving order
            const selected_rows = Array.from(selected_indices)
                .sort(function (a, b) { return a - b; })
                .map(function (idx) { return report.data[idx]; })
                .filter(Boolean);

            if (!selected_rows.length) {
                frappe.msgprint(__("Could not map selected rows."));
                return;
            }

            const canvas = _build_report_canvas(report, selected_rows);
            canvas.toBlob(function (blob) {
                navigator.clipboard.write([
                    new ClipboardItem({ "image/png": blob })
                ]).then(function () {
                    frappe.show_alert({
                        message: __("Selected rows copied! Paste in WhatsApp."),
                        indicator: "green"
                    }, 3);
                }).catch(function (err) {
                    console.error("Clipboard error:", err);
                    frappe.msgprint(__("Clipboard copy failed."));
                });
            }, 'image/png');

        } catch (err) {
            console.error("Copy selected error:", err);
            frappe.msgprint(__("Copy failed. See console."));
        }
    }, 30);
}