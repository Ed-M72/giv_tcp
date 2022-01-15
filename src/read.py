# -*- coding: utf-8 -*-
# version 2021.01.13
import array
import sys
import json
import logging
import datetime
from settings import GiV_Settings
from givenergy_modbus.client import GivEnergyClient
from givenergy_modbus.model.inverter import Inverter, Model
from givenergy_modbus.model.battery import Battery
from givenergy_modbus.model.register_cache import RegisterCache

Print_Raw=False
if GiV_Settings.Print_Raw_Registers.lower()=="true":
    Print_Raw=True

if GiV_Settings.debug.lower()=="true":
    logging.basicConfig(filename='givtcp_debug.log', encoding='utf-8', level=logging.DEBUG)
else:
    logging.basicConfig(filename='givtcp_debug.log', encoding='utf-8', level=logging.INFO)
    
def runAll():
    energy_total_output={}
    energy_today_output={}
    power_output={}
    controlmode={}
    power_flow_output={}
    invertor={}
    batteries = []
    multi_output={}
    temp={}
    logging.info("----------------------------Starting----------------------------")
    logging.info("Getting All Registers")
    
    #Connect to Invertor and load data
    try:
        client=GivEnergyClient(host=GiV_Settings.invertorIP)
        InvRegCache = RegisterCache()
        client.update_inverter_registers(InvRegCache)
        GEInv=Inverter.from_orm(InvRegCache)

        for x in range(0, GiV_Settings.numBatteries):
            BatRegCache = RegisterCache()
            client.update_battery_registers(BatRegCache, battery_number=x)
            GEBat=Battery.from_orm(BatRegCache)
            batteries.insert(x, GEBat)

        logging.info("Invertor connection successful, registers retrieved")
    except:
        e = sys.exc_info()
        logging.error("Error collecting registers: " + str(e))
        temp['result']="Error collecting registers: " + str(e)
        return json.dumps(temp)

    if Print_Raw:
        multi_output['raw/invertor/'+GEInv.inverter_serial_number]=GEInv.dict()
        for b in batteries:
            multi_output['raw/battery/'+b.battery_serial_number]=b.dict()

    try:
    #Total Energy Figures
        logging.info("Getting Total Energy Data")
        energy_total_output['Export Energy Total kWh']=round(GEInv.e_grid_out_total,2)
        energy_total_output['Battery Throughput Total kWh']=round(GEInv.e_battery_discharge_total_2,2)
        energy_total_output['AC Charge Energy Total kWh']=round(GEInv.e_inverter_in_total,2)
        energy_total_output['Import Energy Total kWh']=round(GEInv.e_grid_in_total,2)
        energy_total_output['Invertor Energy Total kWh']=round(GEInv.e_inverter_out_total,2)
        energy_total_output['PV Energy Total kWh']=round(GEInv.p_inverter_out,2)    #CHECK-CHECK
        
        if  GEInv.inverter_model==Model.Hybrid:
            energy_total_output['Load Energy Total kWh']=round((energy_total_output['Invertor Energy Total kWh']-energy_total_output['AC Charge Energy Total kWh'])-(energy_total_output['Export Energy Total kWh']-energy_total_output['Import Energy Total kWh']),3)
            energy_total_output['Battery Charge Energy Total kWh']=GEInv.e_battery_charge_total
            energy_total_output['Battery Discharge Energy Total kWh']=round(GEInv.e_battery_discharge_total,2)
        else:
            energy_total_output['Load Energy Total kWh']=round((energy_total_output['Invertor Energy Total kWh']-energy_total_output['AC Charge Energy Total kWh'])-(energy_total_output['Export Energy Total kWh']-energy_total_output['Import Energy Total kWh'])+energy_total_output['PV Energy Total kWh'],3)

        if GEInv.inverter_model==Model.Hybrid: 
            energy_total_output['Battery Charge Energy Total kWh']=GEInv.e_battery_discharge_total_2
            energy_total_output['Battery Discharge Energy Total kWh']=GEInv.e_battery_discharge_total_2
        
        energy_total_output['Self Consumption Energy Total kWh']=round(energy_total_output['PV Energy Total kWh']-energy_total_output['Export Energy Total kWh'],2)

#Energy Today Figures
        logging.info("Getting Today Energy Data")
        energy_today_output['Battery Throughput Today kWh']=round(GEInv.e_battery_charge_day+GEInv.e_battery_discharge_day,2)
        energy_today_output['PV Energy Today kWh']=round(GEInv.e_pv1_day+GEInv.e_pv2_day,2)
        energy_today_output['Import Energy Today kWh']=round(GEInv.e_grid_in_day,2)
        energy_today_output['Export Energy Today kWh']=round(GEInv.e_grid_out_day,2)
        energy_today_output['AC Charge Energy Today kWh']=round(GEInv.e_inverter_in_day,2)
        energy_today_output['Invertor Energy Today kWh']=round(GEInv.e_inverter_out_total,2)
        energy_today_output['Battery Charge Energy Today kWh']=round(GEInv.e_battery_charge_day,2)
        energy_today_output['Battery Discharge Energy Today kWh']=round(GEInv.e_battery_discharge_day,2)
        energy_today_output['Import for Load Energy Today kWh']=round(GEInv.e_grid_in_day - GEInv.e_inverter_in_day,2)
        energy_today_output['Self Consumption Energy Today kWh']=round(energy_today_output['PV Energy Today kWh']-energy_today_output['Export Energy Today kWh'],2)
                
        if GEInv.inverter_model==Model.Hybrid: 
            energy_today_output['Load Energy Today kWh']=round((energy_today_output['Invertor Energy Today kWh']-energy_today_output['AC Charge Energy Today kWh'])-(energy_today_output['Export Energy Today kWh']-energy_today_output['Import Energy Today kWh']),3)
        else:
            energy_today_output['Load Energy Today kWh']=round((energy_today_output['Invertor Energy Today kWh']-energy_today_output['AC Charge Energy Today kWh'])-(energy_today_output['Export Energy Today kWh']-energy_today_output['Import Energy Today kWh'])+energy_today_output['PV Energy Today kWh'],3)

        
############  Core Power Stats    ############

    #PV Power
        logging.info("Getting PV Power")
        PV_power_1=GEInv.p_pv1
        PV_power_2=GEInv.p_pv2
        PV_power=PV_power_1+PV_power_2
        if PV_power<15000:
            power_output['PV Power String 1']= PV_power_1
            power_output['PV Power String 2']= PV_power_2
            power_output['PV Power']= PV_power

    #Grid Power
        logging.info("Getting Grid Power")
        grid_power= GEInv.p_grid_out
        if grid_power<0:
            import_power=abs(grid_power)
            export_power=0
        elif grid_power>0:
            import_power=0
            export_power=abs(grid_power)
        else:
            import_power=0
            export_power=0
        power_output['Grid Power']=grid_power
        power_output['Import Power']=import_power
        power_output['Export Power']=export_power

    #EPS Power
        logging.info("Getting EPS Power")
        power_output['EPS Power']= GEInv.p_eps_backup

    #Invertor Power
        logging.info("Getting PInv Power")
        Invertor_power=GEInv.p_inverter_out
        if -6000 <= Invertor_power <= 6000:
            power_output['Invertor Power']= Invertor_power
        if Invertor_power<0:
            power_output['AC Charge Power']= abs(Invertor_power)

    #Load Power
        logging.info("Getting Load Power")
        Load_power=GEInv.p_load_demand 
        if Load_power<15500:
            power_output['Load Power']=Load_power

    #Self Consumption
        logging.info("Getting Self Consumption Power")
        power_output['Self Consumption Power']=max(Load_power - import_power,0)

    #Battery Power
        Battery_power=GEInv.p_battery 
        if Battery_power>=0:
            discharge_power=abs(Battery_power)
            charge_power=0
        elif Battery_power<=0:
            discharge_power=0
            charge_power=abs(Battery_power)
        power_output['Battery Power']=Battery_power
        power_output['Charge Power']=charge_power
        power_output['Discharge Power']=discharge_power

    #SOC
        logging.info("Getting SOC")
        power_output['SOC']=GEInv.battery_percent

############  Power Flow Stats    ############

    #Solar to H/B/G
        logging.info("Getting Solar to H/B/G Power Flows")
        if PV_power>0:
            S2H=min(PV_power,Load_power)
            power_flow_output['Solar to House']=S2H
            S2B=max((PV_power-S2H)-export_power,0)
            power_flow_output['Solar to Battery']=S2B
            power_flow_output['Solar to Grid']=max(PV_power - S2H - S2B,0)

        else:
            power_flow_output['Solar to House']=0
            power_flow_output['Solar to Battery']=0
            power_flow_output['Solar to Grid']=0

    #Battery to House
        logging.info("Getting Battery to House Power Flow")
        B2H=max(discharge_power-export_power,0)
        power_flow_output['Battery to House']=B2H

    #Grid to Battery/House Power
        logging.info("Getting Grid to Battery/House Power Flow")
        if import_power>0:
            power_flow_output['Grid to Battery']=charge_power-max(PV_power-Load_power,0)
            power_flow_output['Grid to House']=max(import_power-charge_power,0)

        else:
            power_flow_output['Grid to Battery']=0
            power_flow_output['Grid to House']=0

    #Battery to Grid Power
        logging.info("Getting Battery to Grid Power Flow")
        if export_power>0:
            power_flow_output['Battery to Grid']=max(discharge_power-B2H,0)
        else:
            power_flow_output['Battery to Grid']=0

    #Get Invertor Temperature


    #Combine all outputs
        multi_output["Energy/Total"]=energy_total_output
        multi_output["Energy/Today"]=energy_today_output
        multi_output["Power"]=power_output
        multi_output["Power/Flows"]=power_flow_output
        multi_output["Invertor Details"]=invertor

    ################ Run Holding Reg now ###################
        logging.info("Getting mode control figures")
        # Get Control Mode registers
        shallow_charge=GEInv.battery_soc_reserve
        self_consumption=GEInv.battery_power_mode 
        charge_enable=GEInv.enable_charge
        if charge_enable==True:
            charge_enable="Active"
        else:
            charge_enable="Paused"

        #Get Battery Stat registers
        battery_reserve=GEInv.battery_discharge_min_power_reserve
        target_soc=GEInv.charge_target_soc
        discharge_enable=GEInv.enable_discharge
        if discharge_enable==True:
            discharge_enable="Active"
        else:
            discharge_enable="Paused"
        logging.info("Shallow Charge= "+str(shallow_charge)+" Self Consumption= "+str(self_consumption)+" Discharge Enable= "+str(discharge_enable))

        #Get Charge/Discharge Active status
        discharge_state=GEInv.battery_discharge_limit
        discharge_rate=discharge_state*3
        if discharge_rate>100: discharge_rate=100
        if discharge_state==0:
            discharge_state="Paused"
        else:
            discharge_state="Active"
        charge_state=GEInv.battery_charge_limit
        charge_rate=charge_state*3
        if charge_rate>100: charge_rate=100
        if charge_state==0:
            charge_state="Paused"
        else:
            charge_state="Active"


        #Calculate Mode
        logging.info("Calculating Mode...")
        mode=GEInv.system_mode
        logging.info("Mode is: " + str(mode))

        controlmode['Mode']=mode
        controlmode['Battery Power Reserve']=battery_reserve
        controlmode['Target SOC']=target_soc
        controlmode['Charge Schedule State']=charge_enable
        controlmode['Discharge Schedule State']=discharge_enable
        controlmode['Battery Charge State']=charge_state
        controlmode['Battery Discharge State']=discharge_state
        controlmode['Battery Charge Rate']=charge_rate
        controlmode['Battery Discharge Rate']=discharge_rate

        #Grab Timeslots
        timeslots={}
        logging.info("Getting TimeSlot data")
        timeslots['Discharge start time slot 1']=GEInv.discharge_slot_1[0]
        timeslots['Discharge end time slot 1']=GEInv.discharge_slot_1[1]
        timeslots['Discharge start time slot 2']=GEInv.discharge_slot_2[0]
        timeslots['Discharge end time slot 2']=GEInv.discharge_slot_2[1]
        timeslots['Charge start time slot 1']=GEInv.charge_slot_1[0]
        timeslots['Charge end time slot 1']=GEInv.charge_slot_1[1]
        timeslots['Charge start time slot 2']=GEInv.charge_slot_2[0]
        timeslots['Charge end time slot 2']=GEInv.charge_slot_2[1]

        #Get Invertor Details
        invertor={}
        logging.info("Getting Invertor Details")
        if GEInv.battery_type==1: batterytype="Lithium" 
        if GEInv.battery_type==0: batterytype="Lead Acid" 
        invertor['Battery Type']=batterytype
        invertor['Battery Capacity kWh']=round(((GEInv.battery_nominal_capacity*51.2)/1000),2)
        invertor['Invertor Serial Number']=GEInv.inverter_serial_number
        invertor['Battery Serial Number']=GEInv.first_battery_serial_number
        invertor['Modbus Version']=round(GEInv.modbus_version,2)
        if GEInv.meter_type==1: metertype="EM115" 
        if GEInv.meter_type==0: metertype="EM418" 
        invertor['Meter Type']=metertype
        invertor['Invertor Type']= GEInv.inverter_model.name
        invertor['Invertor Temperature']=round(GEInv.temp_inverter_heatsink,2)

        #Get Battery Details
        battery={}
        logging.info("Getting Battery Details")
        for b in batteries:
            sn=b.battery_serial_number
            battery[sn]={}
            battery[sn]['Battery Serial Number']=sn
            battery[sn]['Battery SOC']=b.battery_soc
            battery[sn]['Battery Capacity']=b.battery_full_capacity
            battery[sn]['Battery Design Capacity']=b.battery_design_capacity
            battery[sn]['Battery Remaining Capcity']=b.battery_remaining_capacity
            battery[sn]['Battery Firmware Version']=b.bms_firmware_version
            battery[sn]['Battery Cells']=b.battery_num_cells
            battery[sn]['Battery Cycles']=b.battery_num_cycles
            battery[sn]['Battery USB present']=b.usb_inserted
            battery[sn]['Battery Temperature']=b.temp_bms_mos
            battery[sn]['Battery Voltage']=b.v_battery_cells_sum

            battery[sn]['Battery Cell 1 Voltage'] = b.v_battery_cell_01
            battery[sn]['Battery Cell 2 Voltage'] = b.v_battery_cell_02
            battery[sn]['Battery Cell 3 Voltage'] = b.v_battery_cell_03
            battery[sn]['Battery Cell 4 Voltage'] = b.v_battery_cell_04
            battery[sn]['Battery Cell 5 Voltage'] = b.v_battery_cell_05
            battery[sn]['Battery Cell 6 Voltage'] = b.v_battery_cell_06
            battery[sn]['Battery Cell 7 Voltage'] = b.v_battery_cell_07
            battery[sn]['Battery Cell 8 Voltage'] = b.v_battery_cell_08
            battery[sn]['Battery Cell 9 Voltage'] = b.v_battery_cell_09
            battery[sn]['Battery Cell 10 Voltage'] = b.v_battery_cell_10
            battery[sn]['Battery Cell 11 Voltage'] = b.v_battery_cell_11
            battery[sn]['Battery Cell 12 Voltage'] = b.v_battery_cell_12
            battery[sn]['Battery Cell 13 Voltage'] = b.v_battery_cell_13
            battery[sn]['Battery Cell 14 Voltage'] = b.v_battery_cell_14
            battery[sn]['Battery Cell 15 Voltage'] = b.v_battery_cell_15
            battery[sn]['Battery Cell 16 Voltage'] = b.v_battery_cell_16

            battery[sn]['Battery Cell 1 Temperature'] = b.temp_battery_cells_1
            battery[sn]['Battery Cell 2 Temperature'] = b.temp_battery_cells_2
            battery[sn]['Battery Cell 3 Temperature'] = b.temp_battery_cells_3
            battery[sn]['Battery Cell 4 Temperature'] = b.temp_battery_cells_4

        #Create multioutput and publish
        multi_output["Timeslots"]=timeslots
        multi_output["Control"]=controlmode
        multi_output["Invertor Details"]=invertor
        multi_output["Battery Details"]=battery
        publishOutput(multi_output,GEInv.inverter_serial_number)
        
    except:
        e = sys.exc_info()
        logging.error("Error processing registers: " + str(e))
        temp['result']="Error processing registers: " + str(e)
        return json.dumps(temp)
    return json.dumps(multi_output, indent=4, sort_keys=True, default=str)

def publishOutput(array,SN):
    safeoutput={}
    tempoutput={}
    # Create a publish safe version of the output
    for p_load in array:
        output=array[p_load]
        safeoutput={}
        for reg in output:
        # Check output[reg] is print safe (not dateTime)
            if isinstance(output[reg], tuple):
                if "slot" in str(reg):
                    logging.info('Converting Timeslots to publish safe string')
                    safeoutput[reg+"_start"]=output[reg][0].strftime("%H%M")
                    safeoutput[reg+"_end"]=output[reg][1].strftime("%H%M")
                else:
                    #Deal with other tuples _ Print each value
                    for index, key in enumerate(output[reg]):
                        logging.info('Converting Tuple to multiple publish safe strings')
                        safeoutput[reg+"_"+str(index)]=str(key)
            elif isinstance(output[reg], datetime.datetime):
                logging.info('Converting datetime to publish safe string')
                safeoutput[reg]=output[reg].strftime("%d-%m-%Y %H:%M:%S")
            elif isinstance(output[reg], datetime.time):
                logging.info('Converting time to publish safe string')
                safeoutput[reg]=output[reg].strftime("%H:%M")
            elif isinstance(output[reg], Model):
                logging.info('Converting time to publish safe string')
                safeoutput[reg]=output[reg].name
            else:
                safeoutput[reg]=output[reg]
        tempoutput[p_load]=safeoutput


    if GiV_Settings.MQTT_Output.lower()=="true":
        from mqtt import GivMQTT
        logging.info("Publish all to MQTT")
        if GiV_Settings.MQTT_Topic=="":
            GiV_Settings.MQTT_Topic="GivEnergy"
        GivMQTT.multi_MQTT_publish(str(GiV_Settings.MQTT_Topic+"/"+SN+"/"), tempoutput)
    if GiV_Settings.JSON_Output.lower()=="true":
        from GivJson import GivJSON
        logging.info("Pushing JSON output")
        GivJSON.output_JSON(tempoutput)
    if GiV_Settings.Influx_Output.lower()=="true":
        from influx import GivInflux
        logging.info("Pushing output to Influx")
        GivInflux.publish(SN,tempoutput)

if __name__ == '__main__':
    globals()[sys.argv[1]]()

