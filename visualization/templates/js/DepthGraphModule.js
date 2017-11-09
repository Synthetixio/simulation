// DepthGraphModule.js

var DepthGraphModule = function (graph_id, width, height) {
	// Create the elements

	// Create the tag:
	var button = $('<button type="button" style="display:block" class="btn btn-sm btn-pad" onclick="toggle_graph('+graph_id+')">'+graph_id+'</button>');
    var div = $("<div id='"+graph_id+"' class=''></div>");

	// Create the tag:
	var canvas_tag = "<canvas style='border:1px dotted'></canvas>";
	// Append it to body:
	var canvas = $(canvas_tag)[0];
	div.append(canvas);

    $("#elements").append($(button)[0]);
	$("#elements").append(div);

	var context = canvas.getContext("2d");

    let data = {
        datasets: [{
                label: 'Bids',
                data: [],
                backgroundColor: "RGBA(255,0,0,0.2)",
                borderColor: "red",
                fill: true,
                pointRadius: 0,
            },
            {
                label: 'Asks',
                data: [],
                backgroundColor: "RGBA(0,255,0,0.2)",
                borderColor: "RGBA(0,255,0,1)",
                fill: true,
                pointRadius: 0,
            }
        ]
    };

    let options = {
        responsive: true,
		maintainAspectRatio: false,

		tooltips: {
			mode: 'index',
			intersect: false,
		},
		hover: {
			mode: 'nearest',
			intersect: true
		},
		scales: {
			xAxes: [{
				display: true,
				type: 'linear',
                position: 'bottom'
			}],
			yAxes: [{
				display: true
			}]
		},
		elements: {
            line: {
                tension: 0, // disables bezier curves
            }
        },
		animation: false
    };

	var chart = new Chart(context, {type: 'line', data: data, options: options});


    this.render = function (step, new_data) {

        this.reset();
        let price_range = 1.0;
        let curr_price = new_data[0];
        let bids = new_data[1];
        let asks = new_data[2];

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
            chart.data.datasets[0].data.unshift(
                {x: this.round(price), y: this.round(cumulative_quant), meta: 'Quant: ' + this.round(cumulative_quant)}
            );
            chart.data.datasets[1].data.unshift(undefined);
            // chart.data.labels.unshift(bids[i][0])
        }
        if (added_bid) {
            chart.data.datasets[0].data.unshift(
                {x:this.round(curr_price * (1 - price_range)), y:chart.data.datasets[0].data[0].y,
                 meta: 'Quant: ' + chart.data.datasets[0].data[0].y}
            );
            chart.data.datasets[1].data.unshift(undefined);
        } else {
            chart.data.datasets[0].data.unshift(
                {x:this.round(curr_price * (1 - price_range)), y:0,
                 meta: 'Quant: ' + 0}
            );
            chart.data.datasets[1].data.unshift(undefined);
        }

        cumulative_quant = 0;

        // push ask data to the chart
        let added_ask = false;
        for (let i in asks) {
            let price = asks[i][0];
            if (price > avg_price * (1 + price_range)) break;
            added_ask = true;
            cumulative_quant += asks[i][1];
            chart.data.datasets[0].data.push(undefined);
            // meta is the "label" that shows up on the tooltip
            // for some reason the x axis is the default value, so show the quant
            chart.data.datasets[1].data.push(
                {x: this.round(price), y: this.round(cumulative_quant), meta: 'Quant: ' + this.round(cumulative_quant)}
            );
            // chart.data.labels.push(price)
        }

        if (added_ask) {
            chart.data.datasets[1].data.push(
                {x:this.round(curr_price * (1 + price_range)),
                    y:chart.data.datasets[1].data[chart.data.datasets[1].data.length-1].y,
                 meta: 'Quant: ' + chart.data.datasets[1].data[chart.data.datasets[1].data.length-1].y}
            );
            chart.data.datasets[0].data.push(undefined);
        } else {
            chart.data.datasets[1].data.push(
                {x:this.round(curr_price * (1 + price_range)), y:0,
                 meta: 'Quant: ' + 0}
            );
            chart.data.datasets[0].data.push(undefined);
        }

        chart.update();
    };

    this.reset = function () {
        chart.data = {datasets: [{
                label: 'Bids',
                data: [],
                backgroundColor: "RGBA(255,0,0,0.2)",
                borderColor: "red",
                fill: true,
                pointRadius: 0,
            },
            {
                label: 'Asks',
                data: [],
                backgroundColor: "RGBA(0,255,0,0.2)",
                borderColor: "RGBA(0,255,0,1)",
                fill: true,
                pointRadius: 0,
            }
        ]};
        chart.data.labels = [];
    };

    this.round = function (value) {
        return Math.floor(value*10000)/10000
    }
};
