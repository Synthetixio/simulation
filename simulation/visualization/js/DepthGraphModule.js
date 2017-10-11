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

    // graph settings
    let price_range = $("#price_range" + graph_id).value; // show +/- % of current price
    let segments = 15; // amount of graph segments, should be odd to leave average in middle
    let half_segments = parseInt((segments - 1) / 2);
    let decimal_places = 3;
    let round_val = Math.pow(10, decimal_places); // for Math.floor(num*val)/val, to get num d.p.

    let databuy = [];
    let datasell = [];
    let labels = [];
    for (let i = 0; i < segments; i++) {
        databuy.push(0);
        datasell.push(0);
        labels.push(i);
    }

    let data = {
        series: [databuy, datasell],
        labels: labels
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
        console.log(price_range, bids, asks);

        let cumulative_quant = 0;
        for (let i in bids) {
            let price = bids[i][0];
            if (price < avg_price * (1 - price_range)) break;

            cumulative_quant += bids[i][1];
            // meta is the "label" that shows up on the tooltip
            // for some reason the x axis is the default value, so show the quant
            chart.data.series[0].unshift(
                {x: price, y: cumulative_quant, meta: 'Quant: ' + cumulative_quant}
            );
            chart.data.series[1].unshift(undefined);
            chart.data.labels.unshift(bids[i][0])
        }

        cumulative_quant = 0;

        // push ask data to the chart
        for (let i in asks) {
            let price = asks[i][0];
            if (price > avg_price * (1 + price_range)) break;
            cumulative_quant += asks[i][1];
            chart.data.series[0].push(undefined);
            // meta is the "label" that shows up on the tooltip
            // for some reason the x axis is the default value, so show the quant
            chart.data.series[1].push(
                {x: price, y: cumulative_quant, meta: 'Quant: ' + cumulative_quant}
            );
            chart.data.labels.push(price)
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
};
