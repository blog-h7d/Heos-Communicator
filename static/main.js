$(window).load(function(){

    Vue.filter('exists', function(obj){
                console.log(obj);
                return obj != Null
            })

    heos_app_ = new Vue({
        el: "#heosapp",
        data:{
            devices:[],
            selected_device:{},
            device_selected:false
        },
        methods:{
          refresh: async function(){
            this.device_selected = false;
            this.selected_device = {}

            response = await fetch('/heos_devices/');
            data = await response.json();
            this.devices = data;
          },
          select: async function(device){
            this.selected_device = device;
            this.devices.forEach(element => element.selected = false)
            device.selected = true;
            this.device_selected = true;
          },
          get_device: function(pid){
            return this.devices.find(element => element.pid == pid)
          },
          update_device: async function(pid)
          {
            // TODO better implementation
            await this.refresh();
            this.select(this.get_device(pid));
          }
        },
        async mounted(){
            await this.refresh();
        }
    })


    es = new EventSource('/heos_events/');
    es.onmessage = function (event) {
        data = JSON.parse(event.data)
        data_params = new URLSearchParams(data.message);
        if(data['event'] == 'player_volume_changed')
        {
            device = heos_app_.get_device(data_params.get('pid'))
            device.volume = data_params.get('level')
        }
        if(data.event == 'player_now_playing_changed')
        {
            heos_app_.update_device(data_params.get('pid')).then()
        }
        if(data['event'] == 'player_now_playing_progress')
        {
            device = heos_app_.get_device(data_params.get('pid'))
            //device.now_playing.cur_pos = data_params.get('cur_pos')
            //device.now_playing.duration = data_params.get('duration')
        }
    }
})