/*!
 * chartjs-chart-financial
 * Version: 0.1.0
 *
 * Copyright 2017 Ben McCann
 * Released under the MIT license
 * https://github.com/chartjs/chartjs-chart-financial/blob/master/LICENSE.md
 */
(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){

},{}],2:[function(require,module,exports){
'use strict';

var helpers = Chart.helpers;

module.exports = function(Chart) {

	Chart.defaults.financial = {
		responsive: true,
		maintainAspectRatio: false,

		tooltips: {
		    enabled: false,
			mode: 'index',
			intersect: false,
            position: "nearest",
			callbacks: {
				label: function(tooltipItem, data) {
					if (data.datasets[tooltipItem.datasetIndex].type === 'financial') {
						let index = tooltipItem.index;
                        let o = data.datasets[tooltipItem.datasetIndex].data[index].o.toFixed(4);
                        let h = data.datasets[tooltipItem.datasetIndex].data[index].h.toFixed(4);
                        let l = data.datasets[tooltipItem.datasetIndex].data[index].l.toFixed(4);
                        let c = data.datasets[tooltipItem.datasetIndex].data[index].c.toFixed(4);
                        let v = data.datasets[tooltipItem.datasetIndex].data[index].v.toFixed(4);
                        let p = data.datasets[tooltipItem.datasetIndex].data[index].p.toFixed(4);

                        return '<br/>Open: ' + o + '<br/>High: ' + h + '<br/>Low: ' + l + '<br/>Close: ' + c +
							'<br/>Volume: '+ v + '<br/>Rolling Price: ' + p;
                    } else {
						return ''
					}
				}
			}
		},
		hover: {
			mode: 'nearest',
			intersect: true
		},

		scales: {
			xAxes: [{
				type: 'time',
				distribution: 'series',
				categoryPercentage: 0.8,
				barPercentage: 0.9,
				time: {
					format: 'll'
				},
				ticks: {
					source: 'data'
				}
			}],
			yAxes: [{
				type: 'financialLinear'
			}]
		}
	};

	/**
	 * This class is based off controller.bar.js from the upstream Chart.js library
	 */
	Chart.controllers.financial = Chart.controllers.bar.extend({

		dataElementType: Chart.elements.Candlestick,

		updateElement: function(candle, index, reset) {
			var me = this;
			var chart = me.chart;
			var meta = me.getMeta();
			var dataset = me.getDataset();
			var custom = candle.custom || {};

			candle._xScale = me.getScaleForId(meta.xAxisID);
			candle._yScale = me.getScaleForId(meta.yAxisID);
			candle._datasetIndex = me.index;
			candle._index = index;

			candle._model = {
				datasetLabel: dataset.label || '',
				//label: '', // to get label value please use dataset.data[index].label

				// Appearance
				upCandleColor: dataset.upCandleColor,
				downCandleColor: dataset.downCandleColor,
				outlineCandleColor: dataset.outlineCandleColor,
				outlineCandleWidth: dataset.outlineCandleWidth,
			};

			me.updateElementGeometry(candle, index, reset);

			candle.pivot();
		},

		/**
		 * @private
		 */
		updateElementGeometry: function(rectangle, index, reset) {
			var me = this;
			var model = rectangle._model;
			var vscale = me.getValueScale();
			var base = vscale.getBasePixel();
			var horizontal = vscale.isHorizontal();
			var ruler = me._ruler || me.getRuler();
			var vpixels = me.calculateBarValuePixels(me.index, index);
			var ipixels = me.calculateBarIndexPixels(me.index, index, ruler);

			model.horizontal = horizontal;
			model.base = reset ? base : vpixels.base;
			model.x = horizontal ? reset ? base : vpixels.head : ipixels.center;
			model.y = horizontal ? ipixels.center : reset ? base : vpixels.head;
			model.height = horizontal ? ipixels.size : undefined;
			model.width = horizontal ? undefined : ipixels.size;
			model.candle = me.calculateCandleValuesPixels(me.index, index);
		},

		/**
		 * @private
		 */
		calculateCandleValuesPixels: function(datasetIndex, index) {
			var me = this;
			var chart = me.chart;
			var scale = me.getValueScale();
			var datasets = chart.data.datasets;

			return {
				o: scale.getPixelForValue(Number(datasets[datasetIndex].data[index].o)),
				h: scale.getPixelForValue(Number(datasets[datasetIndex].data[index].h)),
				l: scale.getPixelForValue(Number(datasets[datasetIndex].data[index].l)),
				c: scale.getPixelForValue(Number(datasets[datasetIndex].data[index].c))
			};
		},

		draw: function() {
			var ctx = this.chart.chart.ctx;
			var elements = this.getMeta().data;
			var dataset = this.getDataset();
			var ilen = elements.length;
			var i = 0;
			var d;

			Chart.canvasHelpers.clipArea(ctx, this.chart.chartArea);

			for (; i < ilen; ++i) {
				d = dataset.data[i].o;
				if (d !== null && d !== undefined && !isNaN(d)) {
					elements[i].draw();
				}
			}

			Chart.canvasHelpers.unclipArea(ctx);
		},

	});
};

},{}],3:[function(require,module,exports){
'use strict';

module.exports = function(Chart) {

	var helpers = Chart.helpers,
		globalOpts = Chart.defaults.global,
		defaultColor = globalOpts.defaultColor;

	globalOpts.elements.candlestick = {
		upCandleColor: "rgba(80, 160, 115, 1)",
		downCandleColor: "rgba(215, 85, 65, 1)",
		outlineCandleColor: "rgba(90, 90, 90, 1)",
		outlineCandleWidth: 1,
	};

	function isVertical(bar) {
		return bar._view.width !== undefined;
	}

	/**
	 * Helper function to get the bounds of the candle
	 * @private
	 * @param bar {Chart.Element.Candlestick} the bar
	 * @return {Bounds} bounds of the bar
	 */
	function getBarBounds(candle) {
		var vm = candle._view;
		var x1, x2, y1, y2;

		var halfWidth = vm.width / 2;
		x1 = vm.x - halfWidth;
		x2 = vm.x + halfWidth;
		y1 = vm.candle.h;
		y2 = vm.candle.l;


		return {
			left: x1,
			top: y1,
			right: x2,
			bottom: y2
		};
	}

	Chart.elements.Candlestick = Chart.Element.extend({
		draw: function() {
			var ctx = this._chart.ctx;
			var vm = this._view;
			var left, right, top, bottom, signX, signY, borderSkipped;
			var borderWidth = vm.borderWidth;


			var x = vm.x;
			var o = vm.candle.o;
			var h = vm.candle.h;
			var l = vm.candle.l;
			var c = vm.candle.c;

			ctx.strokeStyle = helpers.getValueOrDefault(vm.outlineCandleColor, globalOpts.elements.candlestick.outlineCandleColor);
			ctx.lineWidth = helpers.getValueOrDefault(vm.outlineCandleWidth, globalOpts.elements.candlestick.outlineCandleWidth);
			if (c < o) {
				ctx.fillStyle = helpers.getValueOrDefault(vm.upCandleColor, globalOpts.elements.candlestick.upCandleColor);
			} else if (c > o) {
				ctx.fillStyle = helpers.getValueOrDefault(vm.downCandleColor, globalOpts.elements.candlestick.downCandleColor);
			} else {
				ctx.fillStyle = helpers.getValueOrDefault(vm.outlineCandleColor, globalOpts.elements.candlestick.outlineCandleColor);
			}

			ctx.beginPath();
			ctx.moveTo(x, h);
			ctx.lineTo(x, l);
			ctx.stroke();
			ctx.fillRect(x - vm.width / 2, c, vm.width, o - c);
			//ctx.strokeRect(x - vm.width / 2, c, vm.width, o - c);
			ctx.closePath();
		},
		height: function() {
			var vm = this._view;
			return vm.base - vm.y;
		},
		inRange: function(mouseX, mouseY) {
			var inRange = false;

			if (this._view) {
				var bounds = getBarBounds(this);
				inRange = mouseX >= bounds.left && mouseX <= bounds.right && mouseY >= bounds.top && mouseY <= bounds.bottom;
			}

			return inRange;
		},
		inLabelRange: function(mouseX, mouseY) {
			var me = this;
			if (!me._view) {
				return false;
			}

			var inRange = false;
			var bounds = getBarBounds(me);

			if (isVertical(me)) {
				inRange = mouseX >= bounds.left && mouseX <= bounds.right;
			} else {
				inRange = mouseY >= bounds.top && mouseY <= bounds.bottom;
			}

			return inRange;
		},
		inXRange: function(mouseX) {
			var bounds = getBarBounds(this);
			return mouseX >= bounds.left && mouseX <= bounds.right;
		},
		inYRange: function(mouseY) {
			var bounds = getBarBounds(this);
			return mouseY >= bounds.top && mouseY <= bounds.bottom;
		},
		getCenterPoint: function() {
			var vm = this._view;
			var x, y;

			var halfWidth = vm.width / 2;
			x = vm.x - halfWidth;
			y = (vm.candle.h + vm.candle.l) / 2;

			return { x: x, y: y };
		},
		getArea: function() {
			var vm = this._view;
			return vm.width * Math.abs(vm.y - vm.base);
		},
		tooltipPosition: function() {
			var vm = this._view;
			return {
				x: vm.x,
				y: (vm.candle.h + vm.candle.l) / 2
			};
		}
	});

};


},{}],4:[function(require,module,exports){
'use strict';

var Chart = require('chart.js');
Chart = typeof(Chart) === 'function' ? Chart : window.Chart;

require('./element.candlestick.js')(Chart);
require('./scale.financialLinear.js')(Chart);
require('./controller.financial.js')(Chart);

},{"./controller.financial.js":2,"./element.candlestick.js":3,"./scale.financialLinear.js":5,"chart.js":1}],5:[function(require,module,exports){
'use strict';

module.exports = function(Chart) {

	var helpers = Chart.helpers;

	var defaultConfig = {
		position: 'left',
		ticks: {
			// Copied from Ticks.formatters.linear
			callback: function(tickValue, index, ticks) {
				// If we have lots of ticks, don't use the ones
				var delta = ticks.length > 3 ? ticks[2] - ticks[1] : ticks[1] - ticks[0];

				// If we have a number like 2.5 as the delta, figure out how many decimal places we need
				if (Math.abs(delta) > 1) {
					if (tickValue !== Math.floor(tickValue)) {
						// not an integer
						delta = tickValue - Math.floor(tickValue);
					}
				}

				var logDelta = helpers.log10(Math.abs(delta));
				var tickString = '';

				if (tickValue !== 0) {
					var numDecimal = -1 * Math.floor(logDelta);
					numDecimal = Math.max(Math.min(numDecimal, 20), 0); // toFixed has a max of 20 decimal places
					tickString = tickValue.toFixed(numDecimal);
				} else {
					tickString = '0'; // never show decimal places for 0
				}

				return tickString;
			}
		}
	};

	var FinancialLinearScale = Chart.scaleService.getScaleConstructor('linear').extend({

		determineDataLimits: function() {
			var me = this;
			var chart = me.chart;
			var data = chart.data;
			var datasets = data.datasets;
			var isHorizontal = me.isHorizontal();

			function IDMatches(meta) {
				return isHorizontal ? meta.xAxisID === me.id : meta.yAxisID === me.id;
			}

			// First Calculate the range
			me.min = null;
			me.max = null;

			// Regular charts use x, y values
			// For the financial chart we have rawValue.h (hi) and rawValue.l (low) for each point
			helpers.each(datasets, function(dataset, datasetIndex) {
				var meta = chart.getDatasetMeta(datasetIndex);
				if (chart.isDatasetVisible(datasetIndex) && IDMatches(meta)) {
					helpers.each(dataset.data, function(rawValue, index) {
						var high = rawValue.h;
						var low = rawValue.l;
			
						if (me.min === null) {
							me.min = low;
						} else if (low < me.min) {
							me.min = low;
						}
		
						if (me.max === null) {
							me.max = high;
						} else if (high > me.max) {
							me.max = high;
						}
					});
				}
			});

			// Add whitespace around bars. Axis shouldn't go exactly from min to max
			me.min = me.min - me.min * 0.05;
			me.max = me.max + me.max * 0.05;

			// Common base implementation to handle ticks.min, ticks.max, ticks.beginAtZero
			this.handleTickRangeOptions();
		}
	});
	Chart.scaleService.registerScaleType('financialLinear', FinancialLinearScale, defaultConfig);

};

},{}]},{},[4]);
