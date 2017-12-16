// DepthGraphModule.js

var DepthGraphModule = function (group, title, desc, label, width, height) {
    let group_id = (group).replace(/[^a-zA-Z]/g, "");
	let graph_id = (title).replace(/[^a-zA-Z]/g, "");
	// Create the elements
	// var button = $('<button type="button" style="display:block" class="btn btn-sm btn-pad" onclick="toggle_graph('+graph_id+')" >'+title+'</button>');
    // button.tooltip();

    var div = $("<div id='"+graph_id+"' data-for='"+group_id+"' class='graph_div hidden'></div>");

	$("#elements").append(div);
	// Create the context and the drawing controller:


    if ($("#"+group_id)[0] === undefined) {
        var group_link = $("<a href='#' onclick='show_group("+group_id+")' class=\"list-group-item\" id='"+group_id+"'>" + group + "</a>");
        $("#sidebar-list").append(group_link);
    }

    var chart = Highcharts.chart(graph_id, {
        chart: {
			animation: false,
            height: 250,
            type: 'area'
		},
        title: {
            text: title
        },
        subtitle: {
            text: ''
        },
        credits: {
			enabled: false
		},

        xAxis: {
            allowDecimals: true,
            labels: {
                formatter: function () {
                    return this.value; // clean, unformatted number for year
                }
            }
        },
        yAxis: {
            title: {
                text: 'Volume'
            },
            labels: {
                formatter: function () {
                    return this.value;
                }
            }
        },
        plotOptions: {
            area: {
                marker: {
                    enabled: false,
                    symbol: 'circle',
                    radius: 2,
                    states: {
                        hover: {
                            enabled: true
                        }
                    }
                }
            }
        },
        series: [
            {
                name: 'Asks',
                data: [],
                color: 'rgba(120,255,120,0.2)',
                lineColor:'green',
            }, {
                name: 'Bids',
                data: [],
                color:'rgba(255,0,0,0.2)',
                lineColor:'red'
        }]
    });

    this.render = function (step, new_data) {
        if (new_data.length > 0) {
            new_data = new_data[new_data.length-1]
        } else {
            return false;
        }
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
        let _bid_data = [];
        let _ask_data = [];
        for (let i in bids) {
            let price = bids[i][0];
            if (price < avg_price * (1 - price_range)) break;
            added_bid = true;
            cumulative_quant += bids[i][1];
            // meta is the "label" that shows up on the tooltip
            // for some reason the x axis is the default value, so show the quant
            _bid_data.unshift(
                [this.round(price), this.round(cumulative_quant)]
            );
            // _ask_data.unshift(undefined);
            // chart.data.labels.unshift(bids[i][0])
        }
        if (added_bid) {
            _bid_data.unshift(
                [this.round(curr_price * (1 - price_range)), _bid_data[0][1]]
            );
            // _ask_data.unshift(undefined);
        } else {
            _bid_data.unshift(
                [this.round(curr_price * (1 - price_range)), 0]
            );
            // _ask_data.unshift(undefined);
        }

        cumulative_quant = 0;

        // push ask data to the chart
        let added_ask = false;
        for (let i in asks) {
            let price = asks[i][0];
            if (price > avg_price * (1 + price_range)) break;
            added_ask = true;
            cumulative_quant += asks[i][1];
            // _bid_data.push(undefined);
            // meta is the "label" that shows up on the tooltip
            // for some reason the x axis is the default value, so show the quant
            _ask_data.push(
                [this.round(price), this.round(cumulative_quant)]
            );
            // chart.data.labels.push(price)
        }

        if (added_ask) {
            _ask_data.push(
                [this.round(curr_price * (1 + price_range)),
                    _ask_data[_ask_data.length-1][1]]
            );
            // _bid_data.push(undefined);
        } else {
            _ask_data.push(
                [this.round(curr_price * (1 + price_range)), 0]
            );
            // _bid_data.push(undefined);
        }

        chart.series[0].setData(_ask_data);
        chart.series[1].setData(_bid_data);
    };

    this.reset = function () {
    };

    this.round = function (value) {
        return Math.floor(value*10000)/10000
    }
};
