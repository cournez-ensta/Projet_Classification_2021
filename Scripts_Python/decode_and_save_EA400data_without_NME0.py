#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Auteur : Aelaig COURNEZ - Flora GUES - Yann LAMBRECHTS - Romain SAFRAN

# Librairies importee
import numpy as np
import pandas
import struct
import glob
import os
import time
import datetime as dt
from shapely.geometry import  Point, Polygon

#--------------------------------------------------------------------------------#
#               LECTURE ET SAUVEGARDE DES DONNEES EA400                          #
#   Cas ou les donnees de positionnement n'ont pas ete enregistrees dans les     #
#   trames NME0.                                                                 #
#                                                                                #
#   Ce code a pour but de lire des fichiers issus d'acquisitions EA400           #
#   de les decoder et de les enregistrer sous forme de fichiers h5.              #
#   Pour utiliser ce script, il suffit de specifier le dossier ou se trouvent    #
#   les fichiers .raw et .out via la variable d'entree dir_path (main)           #
#   ainsi que le dossier de sortie out_path ou l'on souhaite que les donnees     #
#   soit enregistrees.                                                           #
#   Ce script prend egalement en entree les fichiers de positionnement et        #
#   d'attitude fournis par Qinsy.                                                #                         #
#--------------------------------------------------------------------------------#

#-------- FONCTIONS PERMETTANT DE DECODER LES DIFFERENTES TRAMES --------

def decode_CON0(data):
    """
    Cette fonction permet de decoder les trames CON0.

    Parametres
    ----------
    data : string
        trame CON0 - portion de fichier binaire

    Sortie
    -------
    decode_data : dictionary
        dictionnaire comprenant l'ensemble des parametres d'acquisition

    """
    trame = data[:4]
    if trame == b'CON0':
        decode_data={}
        decode_data["DateTime"] = struct.unpack('<Q', data[4:4+8])[0]
        decode_data["SurveyName"] = struct.unpack('<128s', data[12:12+128])[0].decode('ascii').strip('\x00')
        decode_data["TransectName"] = struct.unpack('<128s', data[140:140+128])[0].decode('ascii').strip('\x00')
        decode_data["SounderName"] = struct.unpack('<128s', data[168:168+128])[0].decode('ascii').strip('\x00')
        decode_data["Spare"] = struct.unpack('128s', data[296:296+128])[0].decode('ascii').strip('\x00')
        # ecart de 100 bits...(?)
        decode_data["TransducerCount"] = struct.unpack('<I', data[524:524+4])[0]
        # transducer 1 = 38kHz
        decode_data["ChannelId_38"] = struct.unpack('128s', data[528:528+128])[0].decode('ascii').strip('\x00')
        decode_data["BeamType_38"] = struct.unpack('<l', data[656:656+4])[0]
        decode_data["Frequency_38"] = struct.unpack('<f', data[660:660+4])[0]
        decode_data["Gain_38"] = struct.unpack('<f', data[664:664+4])[0]
        decode_data["EquivalentBeamAngle_38"] = struct.unpack('<f', data[668:668+4])[0]
        # transducer 2 = 200kHz
        decode_data["ChannelId_200"] = struct.unpack('128s', data[848:848+128])[0].decode('ascii').strip('\x00')
        decode_data["BeamType_200"] = struct.unpack('<l', data[976:976+4])[0]
        decode_data["Frequency_200"] = struct.unpack('<f', data[980:980+4])[0]
        decode_data["Gain_200"] = struct.unpack('<f', data[984:984+4])[0]
        decode_data["EquivalentBeamAngle_200"] = struct.unpack('<f', data[988:988+4])[0]
    return decode_data



def decode_RAW0(data):
    """
    Cette fonction permet de decoder les trames RAW0.

    Parametres
    ----------
    data : string
        trame RAW0 - portion de fichier binaire

    Sortie
    -------
    decode_data : dictionary
        dictionnaire comprenant l'ensemble des donnees associees a un ping/une mesure

    """
    trame = data[:4]
    if trame == b'RAW0':
        decode_data={}
        decode_data["DateTime"] = struct.unpack('<Q', data[4:4+8])[0]
        decode_data["Channel"] = struct.unpack('<h', data[12:12+2])[0]
        decode_data["Mode"] = struct.unpack('<h', data[14:14+2])[0]
        decode_data["TransducerDepth"] = struct.unpack('<f', data[16:16+4])[0]
        decode_data["Frequency"] = struct.unpack('<f', data[20:20+4])[0]
        decode_data["TransmitPower"] = struct.unpack('<f', data[24:24+4])[0]
        decode_data["PulseLength"] = struct.unpack('<f', data[28:28+4])[0]
        decode_data["BandWidth"] = struct.unpack('<f', data[32:32+4])[0]
        decode_data["SampleInterval"] = struct.unpack('<f', data[36:36+4])[0]
        decode_data["SoundVelocity"] = struct.unpack('<f', data[40:40+4])[0]
        decode_data["AbsorptionCoefficient"] = struct.unpack('<f', data[44:44+4])[0]
        decode_data["Heave"] = struct.unpack('<f', data[48:48+4])[0]
        decode_data["Tx_Roll"] = struct.unpack('<f', data[52:52+4])[0]
        decode_data["Tx_Pitch"] = struct.unpack('<f', data[56:56+4])[0]
        decode_data["Temperature"] = struct.unpack('<f', data[60:60+4])[0]
        decode_data["Spare1"] = struct.unpack('<h', data[64:64+2])[0]
        decode_data["Spare2"] = struct.unpack('<h', data[66:66+2])[0]
        decode_data["Rx_Roll"] = struct.unpack('<f', data[68:68+4])[0]
        decode_data["Rx_Pitch"] = struct.unpack('<f', data[72:72+4])[0]
        decode_data["Offset"] = struct.unpack('<l', data[76:76+4])[0]
        decode_data["Count"] = struct.unpack('<l', data[80:80+4])[0]
        decode_data["Power"] = []
        for i in range(decode_data["Count"]):
            decode_data["Power"].append(struct.unpack('<h', data[84+i*2:84+i*2+2])[0]*10*np.log10(2)/256)
    return decode_data



def decode_DEP0(data):
    """
    Cette fonction permet de decoder les trames DEP0.

    Parametres
    ----------
    data : string
        trame DEP0 - portion de fichier binaire

    Sortie
    -------
    decode_data : dictionary
        dictionnaire comprenant les donnes utiles : detection du fond et BS calcule par Kongsberg

    """
    trame = data[:4]
    if trame == b'DEP0':
        decode_data={}
        decode_data["DateTime"] = struct.unpack('<Q', data[4:4+8])[0]
        decode_data["NbChannel"] = struct.unpack('<I', data[12:12+4])[0]
        # transducer 1 = 38kHz
        decode_data["Depth_38"] = struct.unpack('<f', data[16:16+4])[0]
        decode_data["BS_38"] = struct.unpack('<f', data[20:20+4])[0]
        decode_data["Param2_38"] = struct.unpack('<f', data[24:24+4])[0]
        # transducer 2 = 200kHz
        decode_data["Depth_200"] = struct.unpack('<f', data[28:28+4])[0]
        decode_data["BS_200"] = struct.unpack('<f', data[32:32+4])[0]
        decode_data["Param2_200"] = struct.unpack('<f', data[36:36+4])[0]
    return decode_data

    
#--------------- FONCTIONS PERMETTANT DE LIRE LES DONNEES ------------------  
    

def read_RAWfile(f,line,channel,range_detection,depth_max_toSave,angle):
    """
    Cette fonction permet de lire un fichier .raw, puis elle enregistre les donnees dans des dictionnaires.
   

    Parametres
    ----------
    f : .raw file 
        fichier .raw issu de l'EA400 et ouvert grace a : open(filepath, 'rb')
    line : string
        identifiant du fichier de donnees, ici nom de la ligne, par ex : 'L0006'
    channel : list of int
        liste des canaux que l'on souhaite lire, par ex : [1,2] [1], ou [2] avec {1:38kHz ; 2:200kHz}
    range_detection : list of int
        intervalle de profondeur utilise pour la detection du fond, par ex : [5,100]
    depth_max_toSave : int
        profondeur seuil pour la sauvegarde des donnees, ne pas sauvegarder si la profondeur est superieure au seuil
    angle : dictionary
        dictionnaire associant a chaque identifiant de ligne de leve, l'angle de depointage applique

    Sorties
    -------
    d_param : dictionary
        dictionnaire comprenant tous les parametres d'acquisition respectifs a une ligne de leve
    d_power : dictionary
        dictionnaire comprenant l'ensemble des donnees acoustiques mesurees pendant une ligne
    
    """
    #-------------Definition des variables -----------
    
    nb_con , nb_tag , nb_nme , nb_raw , nb_svp , nb_dep = 0,0,0,0,0,0 # compteurs de trames
    ping=0  # compteur de ping
    
    # Origine des dates
    origine_1601 = dt.datetime(year=1601,month=1,day=1,hour = 0,minute = 0,second = 0)
        

    # Dictionnaires a remplir 
    d_power = {}
    d_param = {}
    #--------------------------------------------------

    data = f.read(4 * 1) # Debut de la lecture des donnees 
    
    while len(data)==4 : # Tant qu'il y a toujours des donnees a lire
        
        # on lit la longueur de la trame precisee au debut
        lengths, = struct.unpack('<l', data)
        # on isole la trame dans data
        data = f.read(lengths*1)
        
        trame = data[:4]

        if trame == b'CON0':
            nb_con+=1      
            # on decode la trame CON0
            decoded_CON0 = decode_CON0(data)
        elif trame == b'TAG0':
            nb_tag+=1
        elif trame == b'NME0':
            nb_nme+=1
        elif trame == b'SVP0':
            nb_svp+=1
        elif trame == b'DEP0':
            nb_dep+=1
        
        elif trame == b'RAW0':
            nb_raw+=1
            # on decode la trame RAW0
            decoded_RAW0 = decode_RAW0(data)
        
            # Variables 
            dateTime_ms = (decoded_RAW0["DateTime"]) // 10 # conversion de l'heure de dixieme de ms en ms
            sample_int = decoded_RAW0["SampleInterval"]
            sound_vel = decoded_RAW0["SoundVelocity"]
            power = decoded_RAW0["Power"]
            
            # Conversion des profondeurs en indices
            i_max_save = round( 2*depth_max_toSave / (sample_int * sound_vel)) #i_borne_prof
            i_min_detect = round( 2*range_detection[0] / (sample_int * sound_vel))
            i_max_detect = round( 2*range_detection[1] / (sample_int * sound_vel))
            

        
            if decoded_RAW0["Channel"]==channel: # si la trame est dans la frequence choisie
            
                
                if len(power)!=0:
                    ping += 1
                   

                    # Detection du fond = max de puissance dans l'intervalle range_detect
                    save_power_list = power[:i_max_save+1] # puissance a sauvegarder
                    detect_power_list = power[i_min_detect:i_max_detect+1] # puissance pour detetction du fond
                    max_power = max(detect_power_list) # maximum de puissance dans detect_power_list
                    i_max_power = i_min_detect + detect_power_list.index(max_power) # indice du max
                    prof_max_power = i_max_power * sample_int * sound_vel / 2 # profondeur du max


                    # - - - Stockage des donnees dans les dictionnaires d_param et d_power - - - #
                    
                    # sauvegarde de Power dans un dictionnaire dont la clef est le nom de la ligne
                    # sous forme de dataframe dont l'index est le numero du ping  
     

                        
                    if line not in d_power: # lorsqu'on traite un nouveau fichier, on crée un nouveau DataFrame dans d_power
                        # Initialisation du DataFrame pour d_param, definition des variables
                        d_param[line] = pandas.DataFrame( columns= ['SurveyName','TransectName','SounderName','TransducerCount',
                                                                    'Frequency_38','Gain_38','EquivalentBeamAngle_38',
                                                                    'Frequency_200','Gain_200','EquivalentBeamAngle_200',
                                                                    'Channel','Frequency','Angle',
                                                                    'SampleInterval','SoundVelocity','PulseLength',
                                                                    'BandWidth','AbsorptionCoefficient','Count',
                                                                    'Mode','DepthMaxSave','DepthMinDetect','DepthMaxDetect'])
                        
                        # Enregistrement des metedonnees dans d_param
                        d_param[line].loc['param'] = [decoded_CON0['SurveyName'],decoded_CON0['TransectName'],decoded_CON0['SounderName'],decoded_CON0['TransducerCount'],
                                  decoded_CON0['Frequency_38'],decoded_CON0['Gain_38'],decoded_CON0['EquivalentBeamAngle_38'],
                                  decoded_CON0['Frequency_200'],decoded_CON0['Gain_200'],decoded_CON0['EquivalentBeamAngle_200'],  
                                  channel,decoded_RAW0["Frequency"],angle[line],
                                  decoded_RAW0['SampleInterval'],decoded_RAW0['SoundVelocity'],decoded_RAW0['PulseLength'],
                                  decoded_RAW0['BandWidth'],decoded_RAW0['AbsorptionCoefficient'],decoded_RAW0['Count'],
                                  decoded_RAW0['Mode'],depth_max_toSave,range_detection[0],range_detection[1]]

                    
                        # Initialisation du DataFrame pour d_power, definition des variables
                        d_power[line] = pandas.DataFrame( columns= ['DateTime','Angle','Power','PowerDetectInterval','PowerMax','Depth',
                                                                    'TransmitPower','Mode','TransducerDepth',
                                                                    'Heave','Tx_Roll','Tx_Pitch','Spare1','Spare2',
                                                                    'Rx_Roll','Rx_Pitch','Offset'])
                            
                        # Enregistrement des donnees dans d_power
                        d_power[line].loc[ping,'DateTime'] = origine_1601 + dt.timedelta(microseconds = dateTime_ms)
                        d_power[line].loc[ping,'Angle'] = angle[line]
                        d_power[line].loc[ping,'Power'] = save_power_list
                        d_power[line].loc[ping,'PowerDetectInterval'] = detect_power_list
                        d_power[line].loc[ping,'PowerMax'] = max_power
                        d_power[line].loc[ping,'Depth'] = prof_max_power
                        d_power[line].loc[ping,'TransmitPower'] = decoded_RAW0['TransmitPower']
                        d_power[line].loc[ping,'Mode'] = decoded_RAW0['Mode']
                        d_power[line].loc[ping,'TransducerDepth'] = decoded_RAW0['TransducerDepth']
                        d_power[line].loc[ping,'Heave'] = decoded_RAW0['Heave']
                        d_power[line].loc[ping,'Tx_Roll'] = decoded_RAW0['Tx_Roll']
                        d_power[line].loc[ping,'Tx_Pitch'] = decoded_RAW0['Tx_Pitch']  
                        d_power[line].loc[ping,'Spare1'] = decoded_RAW0['Spare1']  
                        d_power[line].loc[ping,'Spare2'] = decoded_RAW0['Spare2']  
                        d_power[line].loc[ping,'Rx_Roll'] = decoded_RAW0['Rx_Roll']
                        d_power[line].loc[ping,'Rx_Pitch'] = decoded_RAW0['Rx_Pitch']     
                        d_power[line].loc[ping,'Offset'] = decoded_RAW0['Offset']
                        

                    # - - - end Stockage - - - #   
                   
               
        data = f.read(4 * 1)  # Poursuite de la lecture
        # on lit la longueur de la trame precisee à la fin
        lengthf, = struct.unpack('<l', data)
        
        if lengthf != lengths: # on vérifie que l'identifiant est le même au début et à la fin
            raise Exception('Length problem') 
        data = f.read(4 * 1) # Poursuite de la lecture
        
        #----------------- FIN BOUCLE WHILE -----------------

    
    # Nombre de trames au total
    nb_tot = nb_con + nb_tag + nb_nme + nb_raw + nb_svp + nb_dep 
    # Affiche le nom du fichier traité et le nombre de trames qu'il contient
    print('\nFichier : ',f.name)
    print('nb_tot : ',nb_tot,'\nnb_con : ' ,nb_con, '\nnb_tag : ',nb_tag , '\nnb_nme : ',nb_nme , '\nnb_raw : ',nb_raw ,'\nnb_svp : ', nb_svp,'\nnb_dep : ',nb_dep)
    
    return d_param , d_power


def getTrajectory(qinsy_path,line):
    """
    Cette fonction permet de lire les donnees de positionnement et d'attitude enregistrees par Qinsy
    et de les rassembler dans un dictionnaire consacre aux donnees de positionnement.
    
    Parametres
    ----------
    qinsy_path : string
        chemin vers le repertoire des donnees Qinsy
    line : string
        identifiant de la ligne de leve, par ex : 'L0006'

    Sortie
    -------
    d_traj : dictionary
        dictionnaire rassemblant l'ensemble des donnees de positionnement et d'attitude.

    """
    # dictionnaire a remplir    
    d_traj = {}
    # fichiers a traiter
    gyro = glob.glob(qinsy_path+line+'*.Ekinox2_gyro.txt')[0] # gyrometres
    pos = glob.glob(qinsy_path+line+'*.Ekinox2_pos.txt')[0] # position
    prh = glob.glob(qinsy_path+line+'*.Ekinox2_PRH.txt')[0] # attitude
    
    # donnees des gyrometres
    pd_gyro = pandas.read_csv(gyro,skiprows=4,sep=',',names=['DateTime','Gyro','a'])
    pd_gyro = pd_gyro[['DateTime','Gyro']]
    pd_gyro['DateTime'] = pandas.to_datetime(pd_gyro['DateTime'], format='%d/%m/%Y %H:%M:%S.%f')
    # donnees de position
    pd_pos = pandas.read_csv(pos,skiprows=10,sep=',',names=['DateTime','Latitude','Longitude','Easting','Northing','Height','a','b','c'])
    pd_pos = pd_pos[['DateTime','Latitude','Longitude','Easting','Northing','Height']]
    pd_pos['DateTime'] = pandas.to_datetime(pd_pos['DateTime'], format='%d/%m/%Y %H:%M:%S.%f')
    # donnees d'attitude des accelerometres
    pd_prh = pandas.read_csv(prh,skiprows=8,sep=',',names=['DateTime','Pitch','a','Roll','b','Heave','c'])
    pd_prh = pd_prh[['DateTime','Pitch','Roll','Heave']]
    pd_prh['DateTime'] = pandas.to_datetime(pd_prh['DateTime'], format='%d/%m/%Y %H:%M:%S.%f')
    
    merge1 = pd_gyro.merge(pd_pos, on=['DateTime'])
    allTrajData = merge1.merge(pd_prh, on=['DateTime'])
    
    if line not in d_traj:
            
        # Initialisation du DataFrame pour d_traj, definition des variables
        d_traj[line] = pandas.DataFrame( columns= ['DateTime','X','Y','Height','Gyro','Pitch','Roll','Heave'])
    
    # Enregistrement des donnees dans d_traj
    d_traj[line]['DateTime'] = allTrajData['DateTime']
    d_traj[line]['X'] = allTrajData['Easting'] # Sauvegarde des coordonnees en Lambert93
    d_traj[line]['Y'] = allTrajData['Northing']
    d_traj[line]['Height'] = allTrajData['Height']
    d_traj[line]['Gyro'] = allTrajData['Gyro']
    d_traj[line]['Pitch'] = allTrajData['Pitch']
    d_traj[line]['Roll'] = allTrajData['Roll']
    d_traj[line]['Heave'] = allTrajData['Heave']
    
    return d_traj


def interpolate(d_power,d_traj,line):
    """
    Cette fonction permet d'interpoler les donnees de position sur les donnees d'acquisition sonar
    afin d'obtenir le positionnement precis du navire pour chaque sonde.

    Parametres
    ----------
    d_power : dictionary
        dictionnaire comprenant les donnees acoustiques
    d_traj : dictionary
        dictionnaire comprenant les donnees de positionnement
    line : string
        identifiant de la ligne de leve

    Sortie
    -------
    d_power : dictionary
        dictionnaire fourni en entree avec attributs de position supplementaires pour chaque ping.

    """

    # Recuperation des donnees
    df1 = d_power[line]
    df2 = d_traj[line]
    origine = dt.datetime(year=2020, month=10, day=1)  # origine arbitraire fixée au 1 er octobre
    # Liste des dates de mesures de positions GNSS
    temps_pos = df2[['DateTime', 'X', 'Y','Height','Gyro','Pitch','Roll','Heave']].copy()
    temps_pos['DateTime'] = temps_pos['DateTime']- origine
    temps_pos['DateTime'] = temps_pos['DateTime'].dt.total_seconds()
    # Liste des dates de mesures acoustiques
    temps_ping = df1['DateTime']
    temps_ping = temps_ping - origine
    temps_ping = temps_ping.dt.total_seconds()
    df1['DateTime'] = temps_ping
    
    # Initialisation de DataFrame
    f1 = pandas.DataFrame(np.array(temps_ping.values), columns=['DateTime']) # donnees EA400
    temp = np.array(temps_pos.values)
    f2 = pandas.DataFrame(temp, columns=['DateTime', 'X', 'Y','Height','Gyro','Pitch','Roll','Heave']) # donnees trajectoire
    # Interpolation des donnees
    F = f1.append(f2)
    F.set_index('DateTime', inplace=True)
    F = F.sort_index()
    F.interpolate(method='linear', limit_direction='backward', inplace=True)
    F.index.names = ['time']
    F['DateTime'] = F.index
    # Donnees en sortie
    result = pandas.merge(df1, F, on=['DateTime'])
    result['DateTime'] = pandas.to_datetime(result['DateTime'], unit='s', origin=origine)
    d_power[line] = result
    return d_power


def addZone(d_power,line):
    """
    Cette fonction permet d'affecter a chaque ping l'identifiant de la zone ou il se trouve.
    cf. Rapport "Classification des fonds sous-marins par sondeur monofaisceau"

    Parametres
    ----------
    d_power : dictionary
        dictionnaire comprenant l'ensemble des donnees acoustiques pour chaque ping
    line : string
        identifiant de la ligne de leve
        
    Sortie
    -------
    d_power : dictionary
        dictionnaire fourni en entree avec attribut supplementaire 'Zone' associe aux zones d'etude du projet

    """
    data = d_power[line]
    data['Zone'] = np.zeros((data.shape[0]))
    # Definition des zones d'etude
    zone1 = Polygon([[147932, 6830864], [147826, 6830989], [148120, 6831205], [148214, 6831077]])
    zone2 = Polygon([[148026, 6830005], [147945, 6830093], [148170, 6830312], [148255, 6830225]])
    zone3 = Polygon([[147591, 6829582], [147512, 6829661], [147741, 6829883], [147819, 6829805]])
    zone4 = Polygon([[147099, 6829122], [147027, 6829206], [147227, 6829382], [147299, 6829303]])
    zone5 = Polygon([[146456, 6830591], [146434, 6830713], [146726, 6830760], [146754, 6830635 ]])
    # Valeur de l'attribut Zone en fonction de la position des sondes
    for index, row in data.iterrows():
        ping = Point(row['X'],row['Y'])
        if zone1.contains(ping):
            row['Zone']=1
        elif zone2.contains(ping):
            row['Zone']=2
        elif zone3.contains(ping):
            row['Zone']=3
        elif zone4.contains(ping):
            row['Zone']=4
        elif zone5.contains(ping):
            row['Zone']=5
        data.at[index]=row

    d_power[line] = data
    return d_power

    

def read_OUTfile(f,line):
    """
    Cette fonction permet de lire un fichier .out, puis elle enregistre les donnees pertinentes dans des dictionnaires.
    
    Parametres
    ----------
    f : .raw file 
        fichier .raw issu de l'EA400 et ouvert grace a : open(filepath, 'rb')
    line : string
        identifiant du fichier de donnees, ici nom de la ligne, par ex : 'L0006'


    Sorties
    -------
    d_out : dictionary
        dictionnaire comprenant les donnees presentes dans les trames DEP0 : detection du fond et valeur de BS Kongberg

    """
    #-------------Definition des variables -----------
    
    nb_con , nb_tag , nb_nme , nb_raw , nb_svp , nb_dep = 0,0,0,0,0,0 # compteurs de trames
    # Initialisation des listes
    L_time , L_depth38, L_depth200, L_BS38, L_BS200 = [],[],[],[],[]
    # Origine des dates
    origine_1601 = dt.datetime(year=1601,month=1,day=1,hour = 0,minute = 0,second = 0)
    # Dictionnaire a remplir
    d_out = {}
    
    #-------------------------------------------------
    
    data = f.read(4 * 1) # Debut de la lecture des donnees 
    
    while len(data)==4 : # Tant qu'il y a toujours des donnees a lire
        
        # on lit la longueur de la trame precisee au debut
        lengths, = struct.unpack('<l', data)
        # on isole la trame dans data
        data = f.read(lengths*1)
        
        trame = data[:4]

        if trame == b'CON0':
            nb_con+=1      
        elif trame == b'TAG0':
            nb_tag+=1
        elif trame == b'NME0':
            nb_nme+=1
        elif trame == b'RAW0':
            nb_raw+=1
        elif trame == b'SVP0':
            nb_svp+=1
        elif trame == b'DEP0':
            nb_dep+=1
            # on decode la trame DEP0
            decoded_DEP0 = decode_DEP0(data)
            time_ms = (decoded_DEP0['DateTime']) //10 # conversion des dates en ms
            L_time.append(origine_1601 + dt.timedelta(microseconds = time_ms))
            L_depth38.append(decoded_DEP0['Depth_38'])
            L_depth200.append(decoded_DEP0['Depth_200'])
            L_BS38.append(decoded_DEP0['BS_38'])
            L_BS200.append(decoded_DEP0['BS_200'])
            
        data = f.read(4 * 1)  # Poursuite de la lecture
        # on lit la longueur de la trame precisee à la fin
        lengthf, = struct.unpack('<l', data)
        
        if lengthf != lengths: # on vérifie que l'identifiant est le même au début et à la fin
            raise Exception('Length problem') 
        data = f.read(4 * 1) # Poursuite de la lecture
        
        #----------------- FIN BOUCLE WHILE -----------------
    

    if line not in d_out:
        d_out[line] = pandas.DataFrame( columns= ['DateTime','Depth_38','Depth_200','BS_38','BS_200'])
    # Enregistrement des donnees dans d_out
    d_out[line]['DateTime'] = L_time
    d_out[line]['Depth_38'] = L_depth38
    d_out[line]['Depth_200'] = L_depth200
    d_out[line]['BS_38'] = L_BS38
    d_out[line]['BS_200'] = L_BS200
        
    # Nombre de trames au total
    nb_tot = nb_con + nb_tag + nb_nme + nb_raw + nb_svp + nb_dep 
    # Affiche le nom du fichier traité et le nombre de trames qu'il contient
    print('\nFichier : ',f.name)
    print('nb_tot : ',nb_tot,'\nnb_con : ' ,nb_con, '\nnb_tag : ',nb_tag , '\nnb_nme : ',nb_nme , '\nnb_raw : ',nb_raw ,'\nnb_svp : ', nb_svp,'\nnb_dep : ',nb_dep)
    
    return d_out
    
   
    
def save_RAWbdd(outpath,channel,d_param,d_power,d_traj):
    """
    Cette fonction permet de sauvegarder les donnees des fichiers .RAW rassemblees dans les dictionnaires dans des fichiers h5.

    Parametres
    ----------
    outpath : string
        chemin vers le dossier de sortie
    channel : int
        canal a sauvegarder, par ex : 1->38kHz et 2->200kHz
    d_param : dictionary
        dictionnaire comprenant tous les parametres d'acquisition respectifs a une ligne de leve
    d_power : dictionary
        dictionnaire comprenant l'ensemble des donnees acoustiques mesurees pendant une ligne
    d_traj : dictionary
        dictionnaire comprenant l'ensemble des donnees de positionnement recueillies pendant une ligne

    """
    # Prise en compte de la frequence
    if channel ==1: str_freq = '_38kHz'
    else : str_freq = '_200kHz'
    
    for ligne in d_power: # on parcourt les fichiers/lignes traitees
        
        fic_h5_data = ligne +str_freq+ '_data.h5' # nom du fichier de sortie rassemblant les donnees
        
        # Verification pour ne pas ecraser de fichier
        if os.path.exists(outpath + fic_h5_data) :
            fic_h5_data = ligne +str_freq+ '_data2.h5' # cas ou une ligne de leve est enregistree dans deux fichiers
            
        # Creation d'un fichier de sortie h5
        store = pandas.HDFStore(outpath + fic_h5_data)
        store['data'] = d_power[ligne]
        store['trajectoire'] = d_traj[ligne]
        store['param'] = d_param[ligne]
        store.close()
            
    return None



def check_FileExists(filepath):
    """
    Cette fonction permet de verifier qu'aucun fichier n'est ecrase involontairement lors d'une sauvegarde.

    Parametres
    ----------
    filepath : string
        Chemin vers le fichier qu'on souhaite sauvegarde

    Sorties
    -------
    Save : boolean
        False si un fichier existe donc on desactive la sauvegarde
        True si ce fichier n'existe pas, sauvegarde possible

    """
    Save = True # Activation de la sauvegarde
    if os.path.exists(filepath) : # on verifie de ne pas ecraser un fichier existant
        print('Vous allez ecraser le fichier '+filepath+',\nvoulez vous le remplacer par celui que vous generez maintenant ?')
        print('Appuyez sur [y] ou [n], et tapez entrer dans la console.')
        action_doublon = input('->')
        if action_doublon == 'n':
            Save = False # On desactive la sauvegarde
        if action_doublon == 'y':
            Save = True
    return Save


def runDECODEandSAVE_RAWfiles(filesRAW_to_read,out_path,channels,range_detection,depth_max_toSave,angle):
    """
    Cette fonction permet d'executer la lecture et la sauvegarde des fichiers .RAW dans des fichiers h5.

    Parametres
    ----------
    filesRAW_to_read : list of string
        liste des chemins vers les fichiers .raw a lire
    out_path : string
        chemin vers le repertoire de sortie
    channels : list of int
        liste des canaux que l'on souhaite lire, par ex : [1,2] [1], ou [2] avec {1:38kHz ; 2:200kHz}
    range_detection : list of int
        intervalle de profondeur utilise pour la detection du fond, par ex : [5,100]
    depth_max_toSave : int
        profondeur seuil pour la sauvegarde des donnees, ne pas sauvegarder si la profondeur est superieure au seuil
    angle : dictionary
        dictionnaire associant a chaque ligne de leve, l'angle de depointage applique
        
    """
    for channel in channels : # on parcourt les canaux
        for file in filesRAW_to_read : # on parcourt les fichiers de donnees .raw
            line = os.path.basename(file)[:5]
            print('-> Lecture du fichier RAW, Ligne : '+line+' Canal : '+str(channel))
            # Ouverture du fichier
            f = open(file, 'rb')
            # lecture des .raw et remplissage des dictionnaires d_power et d_param :
            d_power,d_param = read_RAWfile(f,line,channel,range_detection,depth_max_toSave,angle)
            # lecture des fichiers qinsy et remplissage de d_traj
            d_traj = getTrajectory(qinsy_path,line)
            print('Lecture achevee')
            # interpolation des donnees de position
            interpolate(d_power,d_traj,line)
            print('Interpolation achevee')
            # ajout de la zone
            d_power = addZone(d_power,line)
            print('Ajout Zone achevee')
            print('-> Sauvegarde du fichier RAW, Ligne : '+line+' Canal : '+str(channel))
            # Enregistrement des donnees dans des fichiers h5
            save_RAWbdd(out_path,channel,d_param,d_power,d_traj)
            print('Sauvegarde achevee')
    return None


def runDECODEandSAVE_OUTfiles(filesOUT_to_read,out_path):
    """
    Cette fonction permet d'executer la lecture et la sauvegarde des fichiers .out dans des fichiers h5.

    Parametres
    ----------
    filesOUT_to_read : list of string
        list des chemins vers les fichiers a lire
    out_path : string
        chemin vers le repertoire de sortie

    """
    for file in filesOUT_to_read : # on parcourt les fichiers .out a lire
        line = os.path.basename(file)[:5]
        print('-> Lecture du fichier OUT, Ligne : '+line)
        # Ouverture du fichier
        fic = open(file, 'rb')
        # lecture et remplissage de dictionnaire :
        d_out = read_OUTfile(fic,line)
        print('Lecture achevee')
        print('-> Sauvegarde du fichier OUT, Ligne : '+line)
        out_file = out_path + line + '_ref.txt'
        # Verification pour ne pas ecraser de fichier
        if check_FileExists(out_file):
            # Creation d'un fichier de metadata
            d_out[line].to_csv(out_file ,sep = ' ', index=False)
        print('Sauvegarde achevee')
    return None


if __name__ == '__main__':
    
    
    t_start = time.time() # Debut du temps de calcul
    
    # Chemins vers les repertoires de donnees
    dir_path = './data/' # repertoire d'entree   ->>> A SPECIFIER
    filesRAW_to_read = glob.glob(dir_path+'*.raw') # Ensemble des fichiers RAW a traiter
    filesOUT_to_read = glob.glob(dir_path+'*.out') # Ensemble des fichiers OUT a traiter
    out_path = './fic_h5/' # repertoire de sortie   ->>> A SPECIFIER
    
    # Donnees de positionnements et d'attitudes
    qinsy_path = './AllData_gyro_pos_prh_qinsy/'
    
    # Variables 
    channels = [1] # canaux à lire {1:38kHz ; 2:200kHz}
    range_detection = [5,100] # intervalle ou on recherche le fond (en m)
    depth_max_toSave = 100 # profondeur max sauvegardee dans les fichiers h5 (en m)
    
    # angle de depointage associe a chaque ligne de leve
    angle = {'L0001':0,'L0002':0,'L0003':0,'L0004':0,'L0005':0,'L0006':0,'L0007':0,'L0008':0,
             'L0009':0,'L0010':0,'L0011':0,'L0012':0,'L0013':0,'L0014':0,'L0015':0,'L0016':0,
             'L0017':0,'L0018':0,'L0019':0,'L0020':0,'L0021':0,'L0022':0,'L0023':0,'L0024':0,
             'L0025':0,'L0026':0,'L0027':25,'L0028':25,'L0029':25,'L0030':45,'L0031':15,'L0032':65,
             'L0033':5,'L0034':5,'L0035':5,'L0036':65,'L0037':15,'L0038':45,'L0039':25,'L0040':25,
             'L0041':25,'L0042':45,'L0043':15,'L0044':65,'L0045':5,'L0046':25,'L0047':25,'L0048':25
             }
      
    # Lecture et Sauvegarde des fichiers .RAW
    runDECODEandSAVE_RAWfiles(filesRAW_to_read,out_path,channels,range_detection,depth_max_toSave,angle)
    
    # Lecture et Sauvegarde des fichiers .OUT
    runDECODEandSAVE_OUTfiles(filesOUT_to_read,out_path)
    
    # Affichage du temps de calcul
    t_end = time.time() # Fin du temps de calcul
    print('\nCalculation time : ',round((t_end-t_start)/60),'min')