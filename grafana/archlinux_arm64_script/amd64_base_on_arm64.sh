# sudo apt-get update

# sudo apt-get install -y qemu-system
# sudo apt-get install -y qemu-user-static
# sudo apt-get install -y qemu-user

# sudo apt-get install -y binfmt-support

# sudo echo ":qemu-x86_64:M::x86-64::/usr/bin/qemu-x86_64-static:" >> /etc/binfmt.d/qemu-x86_64.conf

# sudo update-binfmts --enable qemu-x86_64

# sudo systemctl restart systemd-binfmt

# ls -l /proc/sys/fs/binfmt_misc/ | grep "qemu-x86_64"

# if ls -l /proc/sys/fs/binfmt_misc/ | grep "qemu-x86_64";
# then
#     echo "qemu-x86_64 is registered"
# else
#     echo "qemu-x86_64 is not registered"
#     echo "ended with error"
#     return
# fi

sudo docker run --privileged --rm tonistiigi/binfmt --install all