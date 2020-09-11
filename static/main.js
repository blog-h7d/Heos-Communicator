$(window).load(function(){

    heos_app_ = new Vue({
        el: "#heosapp",
        data:{
            devices:[]
        },
        methods:{
          refresh: async function(){
            response = await fetch('/heos_devices/');
            data = await response.json();
            this.devices = data;
          }
        },
        async mounted(){
            await this.refresh();
        }
    })
})