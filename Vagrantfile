Vagrant.configure(2) do |config|

    config.vm.box = "ubuntu/focal64"

    config.vm.define "app" do |app|

        app.vm.box = "ubuntu/focal64"

        app.vm.network "forwarded_port", guest: 8000, host: 8000


        app.vm.synced_folder ".", "/vagrant",  :owner=> 'ubuntu', :group=>'users', :mount_options => ['dmode=777', 'fmode=777']

        app.vm.provider "virtualbox" do |vb|
           # Display the VirtualBox GUI when booting the machine
           vb.gui = false

          # Customize the amount of memory on the VM:
          vb.memory = "2048"

        end

        app.vm.provision :shell, path: "vagrant/bootstrap.sh"

    end

end
