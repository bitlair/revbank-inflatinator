RevBank Inflatinator
====================

Dit programma werkt de productlijst van [RevBank](https://github.com/revspace/revbank/) bij om de
verkoopprijzen actueel te houden op basis van de inkoopprijzen.

Er zijn scrapers voor deze supermarkten:

* Albert Heijn
* Sligro


## Installatie
Doe een git clone en zorg dat het om de zo veel tijd draait met bijvoorbeeld een Systemd Timer:
```
# /etc/systemd/system/revbank-inflatinator.service
[Unit]
Description=Update product prices in Revbank

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/revbank-inflatinator/inflatinator/ /home/bank/revbank.products
EnvironmentFile=/etc/revbank-inflatinator/env.conf
User=bank
Group=bank
```

```
# /etc/systemd/system/revbank-inflatinator.timer
[Unit]
Description=Run revbank-inflatinator weekly

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
```

## Configuratie
Inflatinator vereist minimaal versie 6.0 van RevBank. Deze versie introduceert een metadataformaat
waar Inflatinator gebruik van maakt.

Het is vereist om de productbeschrijving te quoten. Metadata komt aan het einde van een regel en is
in `#<key>=<value>` formaat, waar de `=<value>` optioneel is.

Inflatinator zal regels herschrijven met nieuwe prijzen, beschrijvingen en eventueel nieuwe
barcodes. Aliassen en barcodes die je zelf toegevoegd blijven staan.

### Albert Heijn
Zie hier onder voorbeelden van de metadata die toegevoegd moet worden per product:

```
8711327538481  0.80  "Ola Liuk"   #ah=wi162664 #qty=8
8712100340666  0.45  "Ola Raket"  #ah=wi209562 #qty=12
```

De `wi162664` is de SKU van hoe het product heet op de website van de AH, je vind deze in de URL
van de productpagina.

De `qty=8` daar achteraan is het aantal individuele producten per verpakking. Dit is niet heel
betrouwbaar terug te vinden op de pagina, dus je zult het zelf moeten opzoeken.


### Sligro
Het verkrijgen van de prijzen van de Sligro vereist een account. Je configureert deze met
environment variables:
```
SLIGRO_USERNAME=<email>
SLIGRO_PASSWORD=<wachtwoord>
```

Sligro producten zien er zo uit:
```
5000112659184,5000112658873  0.95  "Coca-Cola Cola Zero Sugar (33 cl)"              #sligro
4011100240216,40111216       0.80  "Bounty Kokos Melk Chocolade Singles (57 gram)"  #sligro
```

Alleen een `#sligro` aan het einde van de regel is voldoende, Inflatinator gebruikt de **eerste**
barcode om het product te vinden op de website.

Verpakkingen van de Sligro hebben over het algemeen producten hier in zitten die een andere 
barcode hebben dan de verpakking. Inflatinator schrijft beide barcodes naar dezelfde productregel.
Zo kunnen producten ook afgerekend worden door de doos te scannen.


## Q&A

* Q: Wat nou als een product in de aanbieding is en het is eerder voor meer ingekocht? Maak ik dan
verlies?
  * A: Nee. Inflatinator gebruikt altijd de oorspronkelijke prijs, ookal is er een lopende aanbieding.
