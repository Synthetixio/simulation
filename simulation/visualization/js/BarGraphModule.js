// DepthGraphModule.js


var BarGraphModule = function(graph_id, num_agents, width, height) {
    console.log(Chartist);
    // Create the elements
    // Create the tag:
    var div_tag = "<div id='"+graph_id+"' class='ct-chart'></div>";
    // Append it to body:
    var div = $(div_tag)[0];
    $("body").append(div);
    // Prep the chart properties and series:
    var dataseries = []
    // add 0 for each bin, and a bin label
    bins = []
    for (var i=0; i<num_agents; i++) {
        dataseries.push(num_agents - i)
        bins.push(i);
    }
    var data = {

      labels: bins,
      series: [dataseries]
    };


    var options = {
      axisX: {
        labelInterpolationFnc: function(value, index) {
          return index % 2 === 0 ? value : null;
        }
      },
      fullWidth: true,
      height: height+'px',
      chartPadding: {
        right: 40
      },
      plugins: [Chartist.plugins.tooltip()]
    };
    // Create the chart object
    var chart = new Chartist.Bar('#'+graph_id, data, options);

    this.render = function(new_data) {
        // function to modify the chart data
        var chart_len = chart.data.series[0].length;
        // if chart_len > new_data.len
        for (var i = 0; i < chart_len - new_data.length; i++) {
          chart.data.series[0].pop();
          chart.data.labels.pop();
        }

        // if new_data.len > chart_len
        for (var i = 0; i < new_data.length - chart_len; i++) {
          chart.data.series[0].push(new_data[i]);
          chart.data.labels.push(chart.data.labels.length);
        }

        for (var i in new_data) {
          chart.data.series[0][i] = new_data[i];
        }
        chart.update();
    };

    this.reset = function() {
        for (var i in chart.data.series[0]) {
            chart.data.series[0][i] = 0;
        }
        return;
    };
};
