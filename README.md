# HassLGTV
Home Assistant component for LG Smart TV (2013 edition)

## Install LG Smart TV component
Install this component by downloading the lgsmarttv.py file from this repo.
Place it here ```<config directory>/custom_components/lgsmarttv/{THE 2 DOWNLOADED .py FILES}``` on your Home Assistant instance.
  
## Configure your TV
Smart TV must be reachable by Home Assistant server then they should be connected on the same network.
To enable the plugin write add lgsmarttv component to media_players in your configuration file:
```
media_player:
  - platform: lgsmarttv
    client_secret: <SECRET_KEY>
    client_address: <TV_IPADDRESS>
    client_personal_id: <USER_FRIENDLY_NAME>
```
The configuration data are optional: 
- If ```client_secret``` is left blank, your television will show the secret code in the lower right corner of the screen. 
- If ```client_address``` is left blank, the component will search in your network for your television (better if television hasn't a static IP address). This option is useful if you have more than one compatible television. 
- ```client_personal_id``` is used to recognise the entity in home assistant interface.
