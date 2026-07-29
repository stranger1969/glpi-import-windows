#!/usr/bin/python3

import sys
import re
import mysql.connector
import glob
import json

def parse_mon(mon_filename, parsed_table, glpi, cursor, LocationID, CompID):

    data = list() 
    with open(mon_filename, "r", encoding="utf-16") as file:
        data = json.load(file)

    if type(data) is dict:
        return

    for i in data:
        number = int(i.get('Count'))
        print(f"Count: {number}")
        if number == -1:
            continue

        MonName = parsed_table.get("CsDNSHostName") + " Monitor " + str(number)
        cursor.execute("select id from glpi_monitors where name = %s;", (MonName,))
        if cursor.rowcount == 0:
            cursor.execute("select id from glpi_manufacturers where name = %s;", (i.get("Manufacturer"),))
            if cursor.rowcount == 0:
                cursor.execute("insert into glpi_manufacturers (name, date_mod, date_creation) values(%s, now(), now());", (i.get("Manufacturer"),))
                glpi.commit()
                cursor.execute("select id from glpi_manufacturers where name = %s;", (i.get("Manufacturer"),))
            ManufacturerID = cursor.fetchone()

            cursor.execute("select id from glpi_monitormodels where name = %s;", (i.get("Model"),))
            if cursor.rowcount == 0:
                cursor.execute("insert into glpi_monitormodels (name, date_mod, date_creation) values(%s, now(), now());", (i.get("Model"),))
                glpi.commit()
                cursor.execute("select id from glpi_monitormodels where name = %s;", (i.get("Model"),))
            ModelID = cursor.fetchone()

            cursor.execute("insert into glpi_monitors (name, date_mod, date_creation, monitormodels_id, manufacturers_id, locations_id) values(%s, now(), now(), %s, %s, %s);", (MonName, ModelID[0], ManufacturerID[0], LocationID))
            glpi.commit()

            cursor.execute("select id from glpi_monitors where name = %s;", (MonName,))
            MonID = cursor.fetchone()

            cursor.execute("insert into glpi_assets_assets_peripheralassets (itemtype_asset, items_id_asset, items_id_peripheral, itemtype_peripheral) values(\"Computer\", %s, %s, \"Monitor\");",(CompID, MonID[0]))
            glpi.commit()

def parse_hdd(hdd_filename, parsed_table, glpi, cursor, Location, CompID):

    with open(hdd_filename, "r", encoding="utf16") as hdd_file:
        hdd_list = json.load(hdd_file)

    for i in hdd_list:
        DevId = int(i.get("DeviceId"))
        if DevId == -1:
            continue

        DriveDes = parsed_table.get("CsDNSHostName") + "-" + str(DevId)
        cursor.execute("select id from glpi_deviceharddrives where designation = %s;", (DriveDes,))
        if cursor.rowcount > 0:
            continue

        Model = i.get("FriendlyName")
        Manufacturer = Model.split(maxsplit=1)[0]

        cursor.execute("select id from glpi_deviceharddrivemodels where name = %s;", (Model,))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_deviceharddrivemodels (name) values(%s);", (Model,))
            glpi.commit()
            cursor.execute("select id from glpi_deviceharddrivemodels where name = %s;", (Model,))

        ModelID = cursor.fetchone()

        Type = i.get("MediaType")
        cursor.execute("select id from glpi_deviceharddrivetypes where name = %s;", (Type,))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_deviceharddrivetypes (name) values(%s);", (Type,))
            glpi.commit()
            cursor.execute("select id from glpi_deviceharddrivetypes where name = %s;", (Type,))

        TypeID = cursor.fetchone()

        cursor.execute("select id from glpi_manufacturers where name = %s;", (Manufacturer,))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_manufacturers (name, date_mod, date_creation) values(%s, now(), now());", (Manufacturer,))
            glpi.commit()
            cursor.execute("select id from glpi_manufacturers where name = %s;", (Manufacturer,))

        ManufacturerID = cursor.fetchone()

        cursor.execute("select id from glpi_interfacetypes where name = %s;", (i.get("BusType"),))
        BusTypeId = cursor.fetchone()

        Size = int(i.get("Size"))/1048576

        cursor.execute("insert into glpi_deviceharddrives (designation, interfacetypes_id, manufacturers_id, deviceharddrivemodels_id, deviceharddrivetypes_id, date_mod, date_creation, comment, capacity_default) values(%s, %s, %s, %s, %s, now(), now(), %s, %s);", (DriveDes, BusTypeId[0], ManufacturerID[0], ModelID[0], TypeID[0], i.get("SerialNumber"), str(Size)))
        glpi.commit()

        cursor.execute("select id from glpi_deviceharddrives where designation = %s;", (DriveDes,))
        DriveID = cursor.fetchone()

        cursor.execute("insert into glpi_items_deviceharddrives (items_id, itemtype, deviceharddrives_id, capacity, serial, busID, locations_id) values(%s, \"Computer\", %s, %s, %s, %s, %s);", (CompID, DriveID[0], str(Size), i.get("SerialNumber"), BusTypeId[0], Location))
        glpi.commit()


def parse_ram(ram_filename, parsed_table, glpi, cursor, Location, CompID):
    
    with open(ram_filename, "r", encoding="utf16") as ram_file:
        ram_list = json.load(ram_file)

    for i in ram_list:
        if i.get("DeviceLocator") == "None":
            continue

        StickDes = parsed_table.get("CsDNSHostName") + "-" + i.get("DeviceLocator")

        cursor.execute("select id from glpi_devicememories where designation = %s;", (StickDes,))
        if cursor.rowcount > 0:
            continue

        cursor.execute("select id from glpi_manufacturers where name = %s;", (i.get("Manufacturer"),))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_manufacturers (name, date_mod, date_creation) values(%s, now(), now());", (i.get("Manufacturer"),))
            glpi.commit()
            cursor.execute("select id from glpi_manufacturers where name = %s;", (i.get("Manufacturer"),))

        ManufacturerID = cursor.fetchone()

        MemType = 5
        match i.get("SMBIOSMemoryType"):
            case 20 | 21 | 22 | 24 | 26 | 34:
                MemType = 2
            case 5:
                MemType = 1
            case 17:
                MemType = 3
            case _:
                MemType = 5 # New type added manually - cover all other types

        cursor.execute("insert into glpi_devicememories (designation, frequence, manufacturers_id, size_default, devicememorytypes_id, date_mod, date_creation) values(%s, %s, %s, %s, %s, now(), now());", (StickDes, i.get("Speed"), ManufacturerID[0], i.get("GB"), str(MemType)))
        glpi.commit()

        cursor.execute("select id from glpi_devicememories where designation = %s;", (StickDes,))
        MemID = cursor.fetchone()

        cursor.execute("insert into glpi_items_devicememories (items_id, itemtype, devicememories_id, size, serial, locations_id) values(%s, \"Computer\", %s, %s, %s, %s);", (CompID, MemID[0], i.get("GB"), i.get("SerialNumber"), Location))
        glpi.commit()



def parse_files(info_filename, mon_filename, net_filename, soft_filename, ram_filename, hdd_filename):
    parsed_table = {}
    Location = 0
    ManufacturerID = []
    glpi = mysql.connector.connect(
        host="localhost",
        user="glpi",
        password="glpipass",
        database="glpidb"
    )
    Location = 0
    cursor = glpi.cursor(buffered=True)

    with open(info_filename, "r", encoding="utf16") as info_file:
        parsed_table = json.load(info_file)


    with open(net_filename, "r", encoding="utf16") as net_file:
        net_info = json.load(net_file)

    Note = "IPs: "
    for pairs in net_info:
        IP = pairs.get("IPAddress")
        Prefix = pairs.get("PrefixLength")
        if IP == "127.0.0.1":
            continue
        Note += IP + "/" + str(Prefix) + "\n     "


    location=re.sub(r'-[^-]*$', '', parsed_table.get("CsDNSHostName"))

    cursor = glpi.cursor(buffered=True)
    cursor.execute("select name from glpi_computers where name = %s;", (parsed_table.get("CsDNSHostName"),))
    CompID = 0
    if cursor.rowcount == 0:
        querystr="select id from glpi_manufacturers where name = %s;"

        cursor.execute(querystr, (parsed_table.get("CsManufacturer"),))
        ManafacturerID = cursor.fetchone()
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_manufacturers (name, date_mod, date_creation) values (%s, now(), now());", (parsed_table.get("CsManufacturer"),))
            glpi.commit()
            cursor.execute("select id from glpi_manufacturers where name = %s;", (parsed_table.get("CsManufacturer"),))
            ManafacturerID = cursor.fetchone()

        cursor.execute("select id from glpi_computermodels where name = %s;", (parsed_table.get("CsModel"),))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_computermodels (name, date_mod, date_creation) values(%s, now(), now());;", (parsed_table.get("CsModel"),))
            glpi.commit()
            cursor.execute("select id from glpi_computermodels where name = %s;", (parsed_table.get("CsModel"),))
        ModelID = cursor.fetchone()

        cursor.execute("select id from glpi_locations where name = %s;", (location,))
        if cursor.rowcount == 0:
            room=re.sub(r'^.*-', '', location)
            building=re.sub(r'-[^-]*$', '', location)
            cursor.execute("insert into glpi_locations (name, building, room, completename, level, date_mod, date_creation) values(%s, %s, %s, %s, 1, now(), now());", (location, building, room, location))
            glpi.commit()
            cursor.execute("select id from glpi_locations where name = %s", (location,))

        LocationID = cursor.fetchone()
        print(LocationID)
        Location = LocationID[0]
        print(f"LocationID {Location}")

        cursor.execute("insert into glpi_computers (name, manufacturers_id, computermodels_id, locations_id, comment) values(%s, %s, %s, %s, %s);", (parsed_table.get("CsDNSHostName"), ManafacturerID[0], ModelID[0], LocationID[0], Note))
        glpi.commit()

    cursor.execute("select id from glpi_computers where name = %s;", (parsed_table.get("CsDNSHostName"),))
    CompID = cursor.fetchone()

    if Location == 0:
        cursor.execute("select id from glpi_locations where name = %s;", (location,))
        LocationID = cursor.fetchone()
        Location = LocationID[0]

    parse_mon(mon_filename, parsed_table, glpi, cursor, Location, CompID[0])

    
    cursor.execute("select id from glpi_operatingsystems where name = %s;", (parsed_table.get("OsName"),))
    if cursor.rowcount == 0:
        cursor.execute("insert into glpi_operatingsystems (name, date_creation, date_mod) values(%s, now(), now());", (parsed_table.get("OsName"),))
        glpi.commit()
        cursor.execute("select id from glpi_operatingsystems where name = %s;", (parsed_table.get("OsName"),))

    OsID = cursor.fetchone()

    cursor.execute("select id from glpi_operatingsystemversions where name = %s;", (parsed_table.get("OsVersion"),))
    if cursor.rowcount == 0:
        cursor.execute("insert into glpi_operatingsystemversions (name, date_creation, date_mod) values(%s, now(), now());", (parsed_table.get("OsVersion"),))
        glpi.commit()
        cursor.execute("select id from glpi_operatingsystemversions where name = %s;", (parsed_table.get("OsVersion"),))

    OsVersionID = cursor.fetchone()

    cursor.execute("select id from glpi_items_operatingsystems where items_id = %s;", (CompID[0],))
    if cursor.rowcount == 0:
        cursor.execute("insert into glpi_items_operatingsystems (items_id, itemtype, operatingsystems_id, operatingsystemversions_id, date_creation, date_mod) values(%s, \"Computer\", %s, %s, now(), now());", (CompID[0], OsID[0], OsVersionID[0]))
        glpi.commit()
        cursor.execute("select id from glpi_items_operatingsystems where items_id = %s;", (CompID[0],))

    ItemID = cursor.fetchone()

    with open(soft_filename, "r", encoding="utf16") as soft_file:
        soft = json.load(soft_file)

    for i in soft:
        soft_name = i.get("DisplayName")
        if i.get("DisplayVersion"):
            soft_ver = i.get("DisplayVersion")
        else:
            soft_ver = "Unknown"
        if i.get("Publisher"):
            soft_pub = i.get("Publisher")
        else:
            soft_pub = "Unknown"

        cursor.execute("select id from glpi_manufacturers where name = %s;", (soft_pub,))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_manufacturers (name, date_creation, date_mod) values(%s, now(), now());", (soft_pub,));
            glpi.commit()
            cursor.execute("select id from glpi_manufacturers where name = %s;", (soft_pub,))

        PublisherID = cursor.fetchone()

        cursor.execute("select id from glpi_softwares where name = %s and locations_id = %s;", (soft_name, Location))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_softwares (name, locations_id, manufacturers_id, date_creation, date_mod) values(%s, %s, %s, now(), now());", (soft_name, Location, PublisherID[0]))
            glpi.commit()
            cursor.execute("select id from glpi_softwares where name = %s and locations_id = %s;", (soft_name, Location))

        SoftwareID = cursor.fetchone()

        cursor.execute("select id from glpi_softwareversions where softwares_id = %s and name = %s;", (SoftwareID[0], soft_ver))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_softwareversions (softwares_id, name, date_creation, date_mod) values(%s, %s, now(), now());", (SoftwareID[0], soft_ver))
            glpi.commit()
            cursor.execute("select id from glpi_softwareversions where softwares_id = %s and name = %s;", (SoftwareID[0], soft_ver))

        SotfVersionID = cursor.fetchone()

        cursor.execute("select id from glpi_items_softwareversions where softwareversions_id = %s and items_id = %s;", (SotfVersionID[0], CompID[0]))
        if cursor.rowcount == 0:
            cursor.execute("insert into glpi_items_softwareversions (items_id, itemtype, softwareversions_id) values(%s, \"Computer\", %s);", (CompID[0], SotfVersionID[0]))
            glpi.commit()


    parse_hdd(hdd_filename, parsed_table, glpi, cursor, Location, CompID[0])
    parse_ram(ram_filename, parsed_table, glpi, cursor, Location, CompID[0])
    cursor.close()
    glpi.close()


workdir = '[PATH_TO_INFO_FILES]'
mask = '*_info.txt'

for info_filename in glob.glob(workdir + mask):
    mon_filename=re.sub('_info', '_mon', info_filename)
    net_filename=re.sub('_info', '_net', info_filename)
    soft_filename=re.sub('_info', '_soft', info_filename)
    ram_filename=re.sub('_info', '_ram', info_filename)
    hdd_filename=re.sub('_info', '_hdd', info_filename)
    parse_files(info_filename, mon_filename, net_filename, soft_filename, ram_filename, hdd_filename)

