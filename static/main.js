$(window).load(function () {

    // eslint-disable-next-line no-undef
    let TreeList = httpVueLoader('./templates/TreeList.vue')

    Vue.component('TreeList',
        {
            template: TreeList
        }
    )

    Vue.filter('exists', function (obj) {
        console.log(obj);
        return obj != null;
    })

    // eslint-disable-next-line no-undef
    heos_app_ = new Vue({
        el: "#heosapp",
        components:{
            'tree-list': TreeList
        },
        data: {
            devices: [],
            sources: [],
            selected_device: {},
            device_selected: false
        },
        async mounted() {
            await this.refresh();
        },
        methods: {
            refresh: async function () {
                this.device_selected = false;
                this.selected_device = {}

                let response = await fetch('/heos_devices/');
                let data = await response.json();
                this.devices = data;

                response = await fetch('/heos_sources/');
                data = await response.json();
                this.sources = data;

            },
            select: async function (device) {
                this.selected_device = device;
                this.devices.forEach(element => element.selected = false)
                device.selected = true;
                this.device_selected = true;
            },
            get_device: function (pid) {
                return this.devices.find(element => element.pid == pid)
            },
            update_device: async function (pid) {
                // TODO better implementation
                await this.refresh();
                await this.select(this.get_device(pid));
            }
        }
    })


    let es = new EventSource('/heos_events/');
    es.onmessage = function (event) {
        let data = JSON.parse(event.data)
        let data_params = new URLSearchParams(data.message);
        if (data['event'] == 'player_volume_changed') {
            let device = heos_app_.get_device(data_params.get('pid'))
            device.volume = data_params.get('level')
        }
        if (data.event == 'player_now_playing_changed') {
            heos_app_.update_device(data_params.get('pid')).then()
        }
        if (data['event'] == 'player_now_playing_progress') {
            let device = heos_app_.get_device(data_params.get('pid'))
            device.now_playing.cur_pos = data_params.get('cur_pos')
            device.now_playing.duration = data_params.get('duration')
        }
    }
})