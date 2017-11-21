
Chart.defaults.global.tooltips.custom = function(tooltipModel) {
    // Tooltip Element
    var tooltipEl = document.getElementById('chartjs-tooltip');
    // Create element on first render
    if (!tooltipEl) {
        tooltipEl = document.createElement('div');
        tooltipEl.id = 'chartjs-tooltip';
        tooltipEl.innerHTML = "<table></table>";
        document.body.appendChild(tooltipEl);
    }

    var titleLines = tooltipModel.title || [];
    for (let i in titleLines) {
        // don't show tooltips for filler data
        if (titleLines[i] === 54321 || titleLines[i] < 0) {
            tooltipEl.style.opacity = 0;
            return;
        }
    }

    // Hide if no tooltip
    if (tooltipModel.opacity === 0) {
        tooltipEl.style.opacity = 0;
        return;
    }

    // Set caret Position
    tooltipEl.classList.remove('above', 'below', 'no-transform');

    if (tooltipModel.yAlign) {
        tooltipEl.classList.add(tooltipModel.yAlign);
    } else {
        tooltipEl.classList.add('no-transform');
    }

    function getBody(bodyItem) {
        return bodyItem.lines;
    }

    // Set Text
    if (tooltipModel.body) {
        var bodyLines = tooltipModel.body.map(getBody);

        var innerHtml = '<thead>';

        for (let i in titleLines) {
            innerHtml += '<tr><th>' + titleLines[i] + '</th></tr>';
        }
        if (titleLines.length === 0) {
            innerHtml += '<tr><th>' + 0 + '</th></tr>';
        }

        innerHtml += '</thead><tbody>';

        bodyLines.forEach(function(body, i) {
            var colors = tooltipModel.labelColors[i];
            var style = 'background:' + colors.backgroundColor;
            style += '; border-color:' + colors.borderColor;
            style += '; border-width: 2px';
            var span = '<span class="chartjs-tooltip-key" style="' + style + '"></span>';
            innerHtml += '<tr><td>' + span + body + '</td></tr>';
        });
        innerHtml += '</tbody>';

        var tableRoot = tooltipEl.querySelector('table');
        tableRoot.innerHTML = innerHtml;
    }

    // `this` will be the overall tooltip
    var position = this._chart.canvas.getBoundingClientRect();

    var doc = document.documentElement;
    var left = (window.pageXOffset || doc.scrollLeft) - (doc.clientLeft || 0);
    var top = (window.pageYOffset || doc.scrollTop)  - (doc.clientTop || 0);

    // Display, position, and set styles for font
    tooltipEl.style.opacity = 1;
    tooltipEl.style.left = position.left + tooltipModel.caretX + left + 'px';
    if (this._chart.config.type === "financial") {

        tooltipEl.style.top = position.top + 20 + top + 'px';
    } else {
        tooltipEl.style.top = position.top + tooltipModel.caretY + top + 'px';
    }
    tooltipEl.style.fontFamily = "Helvetica Neue","Helvetica","Arial","sans-serif";
    tooltipEl.style.fontSize = "12px";
    tooltipEl.style.fontStyle = tooltipModel._fontStyle;
    tooltipEl.style.padding = tooltipModel.yPadding + 'px ' + tooltipModel.xPadding + 'px';
    tooltipEl.style.minWidth = "160px"

}