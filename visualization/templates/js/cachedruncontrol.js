/** runcontrol.js

 Users can reset() the model, advance it by one step(), or run() it through. reset() and
 step() send a message to the server, which then sends back the appropriate data. run() just
 calls the step() method at fixed intervals.

 The model parameters are controlled via the MesaVisualizationControl object.
 */

/**
 * Object which holds visualization parameters.
 *
 * tick: What tick of the model we're currently at
 running: Boolean on whether we have reached the end of the current model
 * fps: Current frames per second.
 */

var fps_default = $('#fps_default')[0].content;

var MesaVisualizationControl = function() {
    this.draw_delay_period = 5;
    this.tick = 0; // Counts at which tick of the model we are.
    this.done = false;
    this.fps = fps_default; // Frames per second
    this.dataset_info = {};
    this.data = {};
    this.description = "";
    this.dataset_name = "";
    this.dataset_max_steps = 1;
};

var player; // Variable to store the continuous player
var control = new MesaVisualizationControl();
var elements = [];  // List of Element objects
var model_params = [];

// Playback buttons
var playPauseButton = $('#play-pause');
var backButton = $('#back');
var stepButton = $('#step');
var resetButton = $('#reset');


var tickControl = $('#tick');

// Sidebar dom access
var sidebar = $("#settings_body");

var agent_settings = $("#agent_settings");
var agent_values = {};

// Open the websocket connection; support TLS-specific URLs when appropriate
var ws = new WebSocket((window.location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");

ws.onopen = function() {
    console.log("Connection opened!");
    send({"type": "get_datasets"}); // Request model parameters when websocket is ready
    control.ready = false;
    return;
};


// Add model parameters that can be edited prior to a model run
var initGUI = function() {

    var onSubmitCallback = function(param_name, value) {
        send({"type": "submit_params", "param": param_name, "value": value});
    };

    var addBooleanInput = function(param, obj) {
        var dom_id = param + '_id';
        var label = $("<p><label for='" + dom_id + "' class='label label-primary'>" + obj.name + "</label></p>")[0];
        var checkbox = $("<input class='model-parameter' id='" + dom_id + "' type='checkbox'/>")[0];
        var input_group = $("<div class='input-group input-group-lg'></div>")[0];
        sidebar.append(input_group);
        input_group.append(label);
        input_group.append(checkbox);
        $(checkbox).bootstrapSwitch({
            'state': obj.value,
            'size': 'small',
            'onSwitchChange': function(e, state) {
                onSubmitCallback(param, state);
            }
        });
    };

    var addNumberInput = function(param, obj) {
        var dom_id = param + '_id';
        var label = $("<p><label for='" + dom_id + "' class='label label-primary'>" + obj.name + "</label></p>")[0];
        var number_input = $("<input class='model-parameter' id='" + dom_id + "' type='number'/>")[0];
        var input_group = $("<div class='input-group input-group-lg'></div>")[0];
        sidebar.append(input_group);
        input_group.append(label);
        input_group.append(number_input);
        $(number_input).val(obj.value);
        $(number_input).on('change', function() {
            onSubmitCallback(param, Number($(this).val()));
        })
    };

    var addSliderInput = function(param, obj) {
        var dom_id = param + '_id';
        var label = $("<p></p>")[0];
        var tooltip = $("<a data-toggle='tooltip' data-placement='top' class='label label-primary'>" + obj.name + "</a>")[0];
        if (obj.description !== null) {
            $(tooltip).tooltip({
                title: obj.description,
                placement: 'right'
            });
        }
        label.append(tooltip);
        var slider_input = $("<input id='" + dom_id + "' type='text' />")[0];
        var input_group = $("<div class='input-group input-group-lg'></div>")[0];
        sidebar.append(input_group);
        input_group.append(label);
        input_group.append(slider_input);
        $(slider_input).slider({
            min: obj.min_value,
            max: obj.max_value,
            value: obj.value,
            step: obj.step,
            ticks: false,
            ticks_labels: false,
            ticks_positions: false
        }).slider('disable');
        $(slider_input).on('change', function() {
            onSubmitCallback(param, Number($(this).val()));
        });
        $(input_group).click();
    };

    var addChoiceInput = function(param, obj) {
        var dom_id = param + '_id';
        var label = $("<p><label for='" + dom_id + "' class='label label-primary'>" + obj.name + "</label></p>")[0];
        sidebar.append(label);

        var dropdown = $("<div class='dropdown'></div>")[0];
        var button = $("<button class='btn btn-default dropdown-toggle' type='button' data-toggle='dropdown'></button>")[0];
        var span = $("<span class='caret'></span>")[0];
        $(button).text(obj.value + " ");
        $(button).id = dom_id;
        $(button).append(span);
        var choice_container = $("<ul class='dropdown-menu' role='menu' aria-labelledby='" + dom_id + "'></ul>")[0];
        for (var i = 0; i < obj.choices.length; i++) {
            var choice = $("<li role='presentation'><a role='menuitem' tabindex='-1' href='#'>" + obj.choices[i] + "</a></li>")[0];
            $(choice).on('click', function() {
                var value = $(this).children()[0].text;
               $(button).text(value + ' ');
               onSubmitCallback(param, value);
            });
            choice_container.append(choice);
        }

        dropdown.append(button);
        dropdown.append(choice_container);
        sidebar.append(dropdown);
    };

    var addTextBox = function(param, obj) {
        var well = $('<div class="well">' + obj.value + '</div>')[0];
        sidebar.append(well);
    };

    var addAgentSliders = function(param, obj) {
        // this will assume only one of these exists

        let data = obj.value;

        let min_val = 0;
        let max_val = 100;
        let step = 0.01;

        let slider_objs = {};

        let total = 0;
        for (let i in data) {
            total += parseFloat(data[i].value);
        }

        for (let i in data) {
            agent_values[i] = data[i].value;
            let label = $("<p></p>")[0];
            let tooltip = $("<a data-toggle='tooltip' data-placement='top' class='label label-primary'>" + data[i].name + "</a>")[0];
            if (data[i].name !== undefined) {
                $(tooltip).tooltip({
                    title: data[i].description,
                    placement: 'left'
                });
            }
            label.append(tooltip);

            let slider_input = $("<input class='agent_sliders' id='" + data[i].name + "' type='text'/>")[0];
            let input_group = $("<div class='input-group input-group-lg'></div>")[0];
            agent_settings.append(input_group);
            input_group.append(label);
            input_group.append(slider_input);

            slider_objs[i] = slider_input;

            $(slider_input).slider({
                name: data[i].name,
                min: min_val,
                max: max_val,
                value: parseFloat(data[i].value)/total*max_val,
                step: step,
                tooltip_position:'right',
                ticks: false,
                ticks_labels: false,
                ticks_positions: false,
                width: '100%'
            }).slider('disable');
            $(slider_input).on('change', function() {
                var slider = $(slider_input)[0];
                var sum = 0;
                var sum_others = 0;

                var slider_group = $(".agent_sliders");

                for (let i in slider_objs) {
                    let item = $(slider_objs[i])[0];
                    if (item !== slider) {
                        sum_others += parseFloat(item.value);
                    }
                    sum += parseFloat(item.value);
                }

                let return_val = {};

                slider_group.each(function () {
                    let item = $(this)[0];
                    if (item !== slider) {
                        let diff = max_val - sum;
                        if (sum_others !== 0) {
                            $(item).slider('setValue', parseFloat(item.value) + (parseFloat(item.value) / sum_others) * diff);
                        } else {
                            $(item).slider('setValue', 0.01);
                        }
                    }
                    return_val[item.id] = parseFloat(item.value)/max_val;
                });

                onSubmitCallback(param, return_val);
            })
        }
    };

    var addParamInput = function(param, option) {
        param = option.name;
        switch (option['param_type']) {
            case 'checkbox':
                addBooleanInput(param, option);
                break;

            case 'slider':
                addSliderInput(param, option);
                break;

            case 'choice':
                addChoiceInput(param, option);
                break;

            case 'number':
                addNumberInput(param, option);   // Behaves the same as just a simple number
                break;

            case 'static_text':
                addTextBox(param, option);
                break;

            case 'agent_fractions':
                addAgentSliders(param, option);
                break;
        }
    };

    $("#settings_body")[0].innerHTML = '';
    $("#agent_settings")[0].innerHTML = '';

    for (var option in model_params) {
        var type = typeof(model_params[option]);
        var param_str = String(option);

        switch (type) {
            case "boolean":
                addBooleanInput(param_str, {'value': model_params[option], 'name': param_str});
                break;
            case "number":
                addNumberInput(param_str, {'value': model_params[option], 'name': param_str});
                break;
            case "object":
                addParamInput(param_str, model_params[option]);    // catch-all for params that use Option class
                break;
        }
    }
};


var parseDatasetInfo = function(dataset) {
    let data;
    for (let i in control.dataset_info) {
        if (control.dataset_info[i].name === dataset) {
            data = control.dataset_info[i];
        }
    }
    if (data === undefined) {
        console.warn("Error: dataset doesn't exist");
        return;
    }

    control.description = data['description'];
    control.dataset_name = data['name'];
    control.dataset_max_steps = data['max_steps'];

    let agent_fractions = data["settings"]["AgentFractions"];

    let agent_fraction_param = {
        name: "Agent fractions",
        param_type: "agent_fractions",
        value: []
    };

    for (let i in agent_fractions) {
        agent_fraction_param.value.push(
            {
                name: i,
                value: agent_fractions[i],
                description: data["settings"]["AgentDescriptions"][i]
            }
        )
    };

    let number_agents_param = {
        name: "Number of agents",
        param_type: 'slider',
        value: data["settings"]["Model"]['num_agents'],
        min_value: data["settings"]["Model"]['num_agents_min'],
        max_value: data["settings"]["Model"]['num_agents_max'],
        step: 1
    };

    let ur_param = {
        name: "Collateralisation ratio max",
        param_type: 'slider',
        value: data["settings"]["Model"]['utilisation_ratio_max'],
        min_value: 0,
        max_value: 1,
        step: 0.05
    };

    model_params = [agent_fraction_param, number_agents_param, ur_param];

};


/** Parse and handle an incoming message on the WebSocket connection. */
ws.onmessage = function(message) {
    var msg = JSON.parse(message.data);
    switch (msg["type"]) {
        case "viz_state":

            var data = msg["data"];

            // workaround for first step being skipped
            if (control.data[control.dataset].length === 0 && data.length > 0) {
                if (data[0][0] !== 1) {
                    control.tick = -1;
                    return;
                }
            }

            for (var i in data) {
                let step = data[i][0];
                let dataset = data[i][1];
                if (control.data[control.dataset].length <= step) {
                    control.data[control.dataset].push(dataset);
                }
            }
            break;

        case "end":
            // We have reached the end of the model
            control.done = true;
            console.log("Done!");
            $(playPauseButton.children()[0]).html("<span style=\"font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);\" class=\"glyphicon glyphicon-stop\"></span>");
            break;
        case "dataset_info":
            control.dataset_info = msg["data"];

            let selector = $("#dataset_selector");
            selector.html = "";
            for (let i in control.dataset_info) {
                selector.append($('<option>', {
                    value: control.dataset_info[i]['name'],
                    text: control.dataset_info[i]['name']
                }));
            }

            control.dataset = "Balanced";
            selector.val(control.dataset).trigger('change');
            break;
        default:
            // There shouldn't be any other message
            console.log("Unexpected message.");
    }
};


/**	 Turn an object into a string to send to the server, and send it. v*/
var send = function(message) {
    msg = JSON.stringify(message);
    ws.send(msg);
};


/** Reset the model, and rest the appropriate local variables. */
var reset = function($e) {
    if ($e !== undefined)
        $e.preventDefault();

    if (!control.ready) {
        return false
    }
    control.dataset = $("#dataset_selector").val();
    if (!(control.dataset in control.data)) {
        control.data[control.dataset] = []
    }
    control.tick = 0;
    control.last_sent = control.data[control.dataset].length - 1;
    control.done = false;
    if (control.running) {
        run();
    }
    // Reset all the visualizations
    clear_graphs();
    parseDatasetInfo(control.dataset);
    initGUI();

    if (!control.running) {
        $(playPauseButton.children()[0]).html('<span style="font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);" class="glyphicon glyphicon-play"></span>');
    } else {
        $(playPauseButton.children()[0]).html('<span style="font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);" class="glyphicon glyphicon-pause"></span>');
    }
    single_step();
    update_graphs(true);
    return false;
};


/** Send a message to the server get the next visualization state. */
var single_step = function() {
    if (control.tick < 0) {
        control.tick = 0;
    }
    control.tick += 1;
    let fps = parseInt(control.fps);
    if (control.tick >= control.data[control.dataset].length && control.last_sent !== control.data[control.dataset].length) {
        control.last_sent = control.data[control.dataset].length;
        if (!control.done) send({"type": "get_steps", "step": control.data[control.dataset].length, "fps": fps, "dataset": control.dataset});
    }

};


/** Step the model forward. */
var back = function($e) {
    if ($e !== undefined) $e.preventDefault();

    if (!control.running) {
        control.tick -= 2;
        single_step();
        update_graphs(true);
    }

    return false;
};


/** Step the model forward. */
var step = function($e) {
    if ($e !== undefined) $e.preventDefault();

    if (!control.running && !control.done) {
        single_step();
        update_graphs(true);
    }
    else if (!control.done) {
        run();
    }
    return false;
};


/** Call the step function at fixed intervals, until getting an end message from the server. */
var run = function($e) {
    // stop the page scrolling on function call
    if ($e !== undefined) $e.preventDefault();
    var anchor = $(playPauseButton.children()[0]);
    if (control.running) {
        control.running = false;
        if (player) {
            clearInterval(player);
            player = null;
        }
        anchor.html("<span style=\"font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);\" class=\"glyphicon glyphicon-play\"></span>");
    }
    else if (!control.done) {
        if (control.data[control.dataset].length <= 1) {
            show_group($(".list-group-item")[1]);
        }
        control.running = true;
        player = setInterval(
            function() {
                if (!control.running) {
                    return;
                }
                single_step();
                update_graphs(false);
            }, 1000/control.fps
        );
        anchor.html("<span style=\"font-size: 16.5px;text-shadow: 0 0 12px rgba(0,255,125,1);\" class=\"glyphicon glyphicon-pause\"></span>");
    }
    return false;
};


// Initilaize buttons on top bar
playPauseButton.on('click', run);
backButton.on('click', back);
stepButton.on('click', step);
resetButton.on('click', reset);


$("#dataset_selector").on('change', function() {
    parseDatasetInfo(control.dataset);
    initGUI();
    control.ready = true;
    reset();
    $("#DatasetDescription")[0].innerHTML =
        "<h4>"+control.dataset_name+":</h4><p>" +
        control.description + '</p>';
    show_group($("#sidebar-hideall")[0]);
});


function update_graphs(force_draw) {
    if (control.tick === 0) {
        tickControl[0].innerHTML = "Tick: " + (control.tick) + "/" + control.dataset_max_steps;
    } else {
        tickControl[0].innerHTML = "Tick: " + (control.tick-1) + "/" + control.dataset_max_steps;
    }

    if (control.tick <= control.data[control.dataset].length) {
        for (var i in elements) {
            let to_render = [];
            for (let j = 0; j < control.tick;  j++) {
                to_render.push(control.data[control.dataset][j][i])
            }

            // send all data up to current tick to be rendered, force draw when specified/every draw_delay_period
            if (to_render.length % control.draw_delay_period === 0 || force_draw === true) {
                elements[i].render(true, to_render);
            } else {
                elements[i].render(false, to_render);
            }
        }
    } else {
        control.tick -= 1;
    }
}


function clear_graphs() {
    // Reset all the visualizations
    for (var i in elements) {
        elements[i].reset();
    }
}


function show_group(group) {
    $(".list-group-item").removeClass("active");
    $(group).addClass("active");
    $(".graph_div").each(function() {
        if (group === undefined || this.dataset.for !== group.id) {
            $(this).removeClass("hidden").addClass("hidden");
        } else {
            $(this).removeClass("hidden");
        }
    });
    update_graphs(true);
    window.dispatchEvent(new Event('resize'));
}


if(window.chrome){
    // apply niceScroll only if chrome to avoid freezes from scroll events.
    $(function() {
        $("html").niceScroll();
    });
}

