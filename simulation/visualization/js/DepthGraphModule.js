// DepthGraphModule.js


var DepthGraphModule = function(graph_id, width, height) {
    console.log(Chartist);
    // Create the elements
    // Create the tag:
    var div_tag = "<div id='" + graph_id + "buys' class='ct-chart'></div>";
    // Append it to body:
    var div = $(div_tag)[0];
    $("body").append(div);
    // Prep the chart properties and series:

    var databuy = [];
    var datasell = [];
    var labels = []
    for (var i = 0; i < 100; i++) {
      databuy.push(0);
      datasell.push(0);
      labels.push(i);
    }

    var data = {
      series:[databuy, datasell],
      labels:labels
    }
    // datasell = {
    //   series:[],
    //   labels:[1,2,3,4,5]
    // }

    var options = {
      axisX: {
        labelInterpolationFnc: function(value, index) {
          return index % 2 === 0 ? value : null;
        }
      },
      fullWidth: true,
      height: height+'px',
      chartPadding: {
        right: 0
      },
      showArea: true,
      showPoint: true,
      plugins: [Chartist.plugins.tooltip()]
    };

    // Create the chart object
    var chart = new Chartist.Line('#'+graph_id+'buys', data, options);

    this.render = function(new_data) {
        buys = new_data[0];
        sells = new_data[1];
        // data is in the form (rate, quantity)

        // TODO: add data to the graphs

        chart.update();
    };

    this.reset = function() {
        // TODO: reset to 0, this is just for testing, to show what it looks like
        for (var i in chart.data.series[0]) {
            i = parseInt(i);
            if (i < chart.data.series[0].length/2) {
              chart.data.series[0][i] = chart.data.series[0].length/2-i;
              chart.data.series[1][i] = 0;
            } else {
              chart.data.series[1][i] = -chart.data.series[0].length/2+i;
              chart.data.series[0][i] = 0;
            }

        }
        // for (var i in chart2.data.series[0]) {
        //     chart2.data.series[0][i] = i+1;
        // }
        return;
    };
};
