// DepthGraphModule.js


var DepthGraphModule = function(graph_id, width, height) {
    // Create the elements
    // Create the tags:
    var div_tag = `<div class="row" style="padding-left: 30px; margin:0">
          <p>`+graph_id+`</p>
          <p style="float:left; padding-right: 5px;">Price range(1%-100%): </p>
          <input type="range" id="price_range`+graph_id+`" value="0.25" min="0" max="1" step="0.01" style="width: 80%"/>
          <div id='`+graph_id+`' class='ct-chart'></div>
          </div>`;
    // Append it to body:
    var div = $(div_tag)[0];
    $("body").append(div);
    // Prep the chart properties and series:

    // graph settings
    var price_range = $("#price_range"+graph_id).value; // show +/- % of current price
    var segments = 15; // amount of graph segments, should be odd to leave average in middle
    var half_segments = parseInt((segments-1)/2);
    var decimal_places = 3;
    var round_val = Math.pow(10,decimal_places); // for Math.floor(num*val)/val, to get num d.p.

    var databuy = [];
    var datasell = [];
    var labels = []
    for (var i = 0; i < segments; i++) {
      databuy.push(0);
      datasell.push(0);
      labels.push(i);
    }

    var data = {
      series:[databuy, datasell],
      labels:labels
    }

    var options = {
      axisX: {
        // hide every 2nd x-axis label to avoid clutter
        labelInterpolationFnc: function(value, index) {
          return index % 2 === 0 ? value : null;
        }
      },
      fullWidth: true,
      height: height+'px',
      chartPadding: {
        right: 30,
        left: -10
      },
      showArea: true,
      showPoint: true,
      plugins: [Chartist.plugins.tooltip()]
    };

    // Create the chart object
    var chart = new Chartist.Line('#'+graph_id, data, options);

    this.render = function(new_data) {

      this.reset();
      var price_range = parseFloat($("#price_range"+graph_id)[0].value);
      var bids = new_data[0];
      var asks = new_data[1];

      // data is sorted by rate, in the form [(rate, quantity) ... ]
      var min_bid=0, max_bid=0, min_ask=0, max_ask=0;
      if (bids.length > 0) {
        min_bid = bids[0][0];
        max_bid = bids[bids.length-1][0];
      }

      if (asks.length > 0) {
        min_ask = asks[0][0];
        max_ask = asks[asks.length-1][0];
      }

      var avg_price = (max_bid+min_ask)/2;

      // render bids
      if (bids.length > 0) {
        var bid_quant = 0; // cumulative quantity of buys
        var i = bids.length-1;
        for (var curr_ind=0; curr_ind<half_segments; curr_ind++) {
          var price = bids[i][0];

          // while the price is less than the "segment" price cap
          while (price > (avg_price*(1-(price_range*curr_ind/half_segments)))) {
            var price = bids[i][0];
            bid_quant += bids[i][1];
            i--;
            if (i<0) {
              break;
            }
          }
          chart.data.series[1][half_segments-curr_ind] = bid_quant;
          // show only some decimal places
          chart.data.labels[half_segments-curr_ind] = Math.round(price * round_val) / round_val;;
        }
      }

      // render asks

      if (asks.length > 0) {
        var ask_quant = 0;
        var i = 0;
        for (var curr_ind=half_segments+1; curr_ind<segments; curr_ind++) {
          var price = asks[i][0];
          while (price < (avg_price*(1+(price_range*(curr_ind-half_segments)/half_segments)))) {
            var price = asks[i][0];
            ask_quant += asks[i][1];
            i++;
            if (i>=asks.length) {
              break;
            }
          }
          chart.data.series[0][curr_ind] = ask_quant;
          // show only some decimal places
          chart.data.labels[curr_ind] = Math.round(price * round_val) / round_val;
        }
      }


      // make any 0 values take the values of its neighbors
      for (var i=half_segments; i>=0;i--) {
        if (chart.data.series[1][i] == 0) {
          chart.data.series[1][i] = chart.data.series[1][i+1];
        }
      }

      for (var i=half_segments+1; i<segments;i++) {
        if (chart.data.series[0][i] == 0) {
          chart.data.series[0][i] = chart.data.series[0][i-1];
        }
      }

      chart.update();
    };

    this.reset = function() {
      for (var i in chart.data.series[0]) {
        chart.data.series[0][i] = 0;
        chart.data.series[1][i] = 0;
        chart.data.labels[i] = '';
      }
    };
};
