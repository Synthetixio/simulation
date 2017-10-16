// DepthGraphModule.js


var DepthGraphModule = function (graph_id, width, height) {
    // Create the elements
    // Create the tags:
    let div_tag = `<div class="row" style="padding-left: 30px; margin:0">
          <p>` + graph_id + `</p>
          <p style="float:left; padding-right: 5px;">Price range(1%-100%): </p>
          <input type="range" id="price_range` + graph_id + `" value="0.25" min="0" max="1" step="0.01" style="width: 80%"/>
          <div id='` + graph_id + `' class='ct-chart'></div>
          </div>`;
    // Append it to body:
    let div = $(div_tag)[0];
    $("body").append(div);
    // Prep the chart properties and series:

    let data = {
        series: [[], []],
        labels: []
    };

    let options = {
        axisX: {
            // hide every 2nd x-axis label to avoid clutter
            labelInterpolationFnc: function (value, index) {
                return index % 2 === 0 ? value : null;
            },
            type: Chartist.AutoScaleAxis
        },
        fullWidth: true,
        height: height + 'px',
        chartPadding: {
            right: 30,
            left: -10
        },
        showArea: true,
        showPoint: true,
        plugins: [Chartist.plugins.tooltip()]
    };

    // Create the chart object
    let chart = new Chartist.Line('#' + graph_id, data, options);

    this.render = function (new_data) {

        this.reset();
        let price_range = parseFloat($("#price_range" + graph_id)[0].value);
        let bids = new_data[0];
        let asks = new_data[1];

        // data is sorted by rate, in the form [(rate, quantity) ... ]
        let max_bid = 0, min_ask = 0;
        if (bids.length > 0) {
            max_bid = bids[0][0];
        }

        if (asks.length > 0) {
            min_ask = asks[0][0];
        }

        let avg_price = (max_bid + min_ask) / 2;

        let cumulative_quant = 0;
        let added_bid = false;
        for (let i in bids) {
            let price = bids[i][0];
            if (price < avg_price * (1 - price_range)) break;
            added_bid = true;
            cumulative_quant += bids[i][1];
            // meta is the "label" that shows up on the tooltip
            // for some reason the x axis is the default value, so show the quant
            chart.data.series[0].unshift(
                {x: this.round(price), y: this.round(cumulative_quant), meta: 'Quant: ' + this.round(cumulative_quant)}
            );
            chart.data.series[1].unshift(undefined);
            chart.data.labels.unshift(bids[i][0])
        }
        if (added_bid) {
            chart.data.series[0].unshift(
                {x:this.round(avg_price * (1 - price_range)), y:chart.data.series[0][0].y,
                 meta: 'Quant: ' + chart.data.series[0][0].y}
            );
            chart.data.series[1].unshift(undefined);
        } else {
            chart.data.series[0].unshift(
                {x:this.round(avg_price * (1 - price_range)), y:0,
                 meta: 'Quant: ' + 0}
            );
            chart.data.series[1].unshift(undefined);
        }

        cumulative_quant = 0;

        // push ask data to the chart
        let added_ask = false;
        for (let i in asks) {
            let price = asks[i][0];
            if (price > avg_price * (1 + price_range)) break;
            added_ask = true;
            cumulative_quant += asks[i][1];
            chart.data.series[0].push(undefined);
            // meta is the "label" that shows up on the tooltip
            // for some reason the x axis is the default value, so show the quant
            chart.data.series[1].push(
                {x: this.round(price), y: this.round(cumulative_quant), meta: 'Quant: ' + this.round(cumulative_quant)}
            );
            chart.data.labels.push(price)
        }

        if (added_ask) {
            chart.data.series[1].push(
                {x:this.round(avg_price * (1 + price_range)), y:chart.data.series[1][chart.data.series[1].length-1].y,
                 meta: 'Quant: ' + chart.data.series[1][chart.data.series[1].length-1].y}
            );
            chart.data.series[0].push(undefined);
        } else {
            chart.data.series[1].push(
                {x:this.round(avg_price * (1 + price_range)), y:0,
                 meta: 'Quant: ' + 0}
            );
            chart.data.series[0].push(undefined);
        }

        chart.update();
    };

    this.reset = function () {
        for (let i in chart.data.series[0]) {
            chart.data.series[0] = [];
            chart.data.series[1] = [];
            chart.data.labels = [];
        }
    };

    this.round = function (value) {
        return Math.floor(value*10000)/10000
    }
};
