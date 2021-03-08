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
from pyproj import Proj, transform

#--------------------------------------------------------------------------------#
#               LECTURE ET SAUVEGARDE DES DONNEES EA400                          #
#   Cas ou les donnees de positionnement sont enregistrees dans les trames NME0. #
#                                                                                #
#   Ce code a pour but de lire des fichiers issus d'acquisitions EA400           #
#   de les decoder et de les enregistrer sous forme de fichiers h5.              #
#   Pour utiliser ce script, il suffit de specifier le dossier ou se trouvent    #
#   les fichiers .raw et .out via la variable d'entree dir_path (main)           #
#   ainsi que le dossier de sortie out_path ou l'on souhaite que les donnees     #
#   soit enregistrees.                                                           #
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



def decode_NME0(data):
    """
    Cette fonction permet de decoder les trames NME0
    /!\ return None si line_[0]!='$GPGGA'

    Parametres
    ----------
    data : string
        trame NME0 - portion de fichier binaire

    Sorties
    -------
    data_traj : list of float
        donnees de postionnement [date en secondes, latitude, longitude, altitude]

    """
    trame = data[:4]
    if trame == b'NME0':
        trames = data[12:].decode('ascii').split('\n')
       
        for line_ in trames:

            line_=line_.split(',')
            if line_[0]=='$GPGGA':
                
                sec_txt = line_[1].split(".")[0]
                secondes = int(sec_txt[-2:]) + int(sec_txt[-4:-2])*60 + int(sec_txt[:-4])*3600
                
                lat=float(line_[2])
                lat=lat//100+(lat-lat//100*100)/60
                
                if line_[3]=='S':
                    lat=-lat
                    
                lon=float(line_[4])
                lon = lon // 100 + (lon - lon // 100*100) / 60
                
                if line_[5]=='W':
                    lon=-lon
                    
                data_traj = [secondes, lat, lon, float(line_[9])+float(line_[11])]             
                return data_traj



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
    

def read_RAWfile(f,line,channel,survey_date,range_detection,depth_max_toSave):
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
    survey_date : datetime
        date a laquelle a ete realisee le leve (jour), par ex : dt.datetime(year=2020,month=10,day=7,hour = 0,minute = 0,second = 0)
    range_detection : list of int
        intervalle de profondeur utilise pour la detection du fond, par ex : [5,100]
    depth_max_toSave : int
        profondeur seuil pour la sauvegarde des donnees, ne pas sauvegarder si la profondeur est superieure au seuil


    Sorties
    -------
    d_param : dictionary
        dictionnaire comprenant tous les parametres d'acquisition respectifs a une ligne de leve
    d_power : dictionary
        dictionnaire comprenant l'ensemble des donnees acoustiques mesurees pendant une ligne
    d_traj : dictionary
        dictionnaire comprenant l'ensemble des donnees de positionnement recueillies pendant une ligne

    """
    #-------------Definition des variables -----------
    
    nb_con , nb_tag , nb_nme , nb_raw , nb_svp , nb_dep = 0,0,0,0,0,0 # compteurs de trames
    ping=0  # compteur de ping
    
    # Sauvegarde des donnees NME0
    Trajectoire_time = [] # liste des temps trajectoire
    Trajectoire_lat,Trajectoire_lon,Trajectoire_z=[],[],[] # listes des latitudes, longitudes et altitudes
    
    # Origine des dates
    origine_1601 = dt.datetime(year=1601,month=1,day=1,hour = 0,minute = 0,second = 0)
        

    # Dictionnaires a remplir
    d_power = {}
    d_param = {}
    d_traj = {}
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
            # on decode la trame NME0
            decoded_NME0 = decode_NME0(data)
            if decoded_NME0 != None:
                Trajectoire_time.append(survey_date + dt.timedelta(seconds = decoded_NME0[0]))
                Trajectoire_lat.append(decoded_NME0[1])
                Trajectoire_lon.append(decoded_NME0[2])
                Trajectoire_z.append(decoded_NME0[3])
                
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
            i_max_save = round( 2*depth_max_toSave / (sample_int * sound_vel)) # i_borne_prof
            i_min_detect = round( 2*range_detection[0] / (sample_int * sound_vel))
            i_max_detect = round( 2*range_detection[1] / (sample_int * sound_vel))
            

        
            if decoded_RAW0["Channel"]==channel: # si la trame est dans la frequence choisie
            
                
                if len(power)!=0:
                    ping += 1
                   

                    # Detection du fond = max de puissance dans l'intervalle range_detection
                    save_power_list = power[:i_max_save+1] # puissance a sauvegarder
                    detect_power_list = power[i_min_detect:i_max_detect+1] # puissance pour detection du fond
                    max_power = max(detect_power_list) # maximum de puissance dans detect_power_list
                    i_max_power = i_min_detect + detect_power_list.index(max_power) # indice du max
                    prof_max_power = i_max_power * sample_int * sound_vel / 2 # profondeur du max


                    # - - - Stockage des donnees dans les dictionnaires d_param et d_power - - - #
                    
                    # extraction de Power dans un dictionnaire dont la clef est le nom de la ligne
                    # sous forme de dataframe dont l'index est le numero du ping  
     
                        
                    if line not in d_power: # lorsqu'on traite un nouveau fichier, on crée un nouveau DataFrame dans d_power
                        # Initialisation du DataFrame pour d_param, definition des variables
                        d_param[line] = pandas.DataFrame( columns= ['SurveyName','TransectName','SounderName','TransducerCount',
                                                                    'Frequency_38','Gain_38','EquivalentBeamAngle_38',
                                                                    'Frequency_200','Gain_200','EquivalentBeamAngle_200',
                                                                    'Channel','Frequency',
                                                                    'SampleInterval','SoundVelocity','PulseLength',
                                                                    'BandWidth','AbsorptionCoefficient','Count',
                                                                    'Mode','DepthMaxSave','DepthMinDetect','DepthMaxDetect'])
                        
                        # Enregistrement des metadonnees dans d_param
                        d_param[line].loc['param'] = [decoded_CON0['SurveyName'],decoded_CON0['TransectName'],decoded_CON0['SounderName'],decoded_CON0['TransducerCount'],
                                  decoded_CON0['Frequency_38'],decoded_CON0['Gain_38'],decoded_CON0['EquivalentBeamAngle_38'],
                                  decoded_CON0['Frequency_200'],decoded_CON0['Gain_200'],decoded_CON0['EquivalentBeamAngle_200'],  
                                  channel,decoded_RAW0["Frequency"],
                                  decoded_RAW0['SampleInterval'],decoded_RAW0['SoundVelocity'],decoded_RAW0['PulseLength'],
                                  decoded_RAW0['BandWidth'],decoded_RAW0['AbsorptionCoefficient'],decoded_RAW0['Count'],
                                  decoded_RAW0['Mode'],depth_max_toSave,range_detection[0],range_detection[1]]

                    
                        # Initialisation du DataFrame pour d_power, definition des variables
                        d_power[line] = pandas.DataFrame( columns= ['DateTime','Power','PowerDetectInterval','PowerMax','Depth',
                                                                    'TransmitPower','Mode','TransducerDepth',
                                                                    'Heave','Tx_Roll','Tx_Pitch','Spare1','Spare2',
                                                                    'Rx_Roll','Rx_Pitch','Offset'])
                            
                        # Enregistrement des donnees dans d_power
                        d_power[line].loc[ping,'DateTime'] = origine_1601 + dt.timedelta(microseconds = dateTime_ms)
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
        
        if lengthf != lengths: # on verifie que l'identifiant est le même au début et à la fin
            raise Exception('Length problem') 
        data = f.read(4 * 1) # Poursuite de la lecture
        
        #----------------- FIN BOUCLE WHILE -----------------


    # # - - - Stockage des metadonnees et des donnees de positionnement dans d_traj - - - #
         
    if line not in d_traj:
        
        # Initialisation du DataFrame pour d_traj, definition des variables
        d_traj[line] = pandas.DataFrame( columns= ['DateTime','lon','lat','X','Y','z'])
    
    # - Conversion des coordonnees de WGS84 en Lambert93 - #
    outProj = Proj('epsg:2154')
    inProj = Proj('epsg:4326') 
    lon, lat = np.array(Trajectoire_lon), np.array(Trajectoire_lat)
    X_L93,Y_L93 = transform(inProj,outProj,lat,lon)   

    # Enregistrement des donnees dans d_traj
    d_traj[line]['DateTime'] = Trajectoire_time
    d_traj[line]['lon'] = Trajectoire_lon # Sauvegarde des coordonnees en WGS84
    d_traj[line]['lat'] = Trajectoire_lat
    d_traj[line]['X'] = X_L93 # Sauvegarde des coordonnees en Lambert93
    d_traj[line]['Y'] = Y_L93
    d_traj[line]['z'] = Trajectoire_z
        
        
    # # - - -  end - - - #
    
    # Nombre de trames au total
    nb_tot = nb_con + nb_tag + nb_nme + nb_raw + nb_svp + nb_dep 
    # Affiche le nom du fichier traite et le nombre de trames qu'il contient
    print('\nFichier : ',f.name)
    print('nb_tot : ',nb_tot,'\nnb_con : ' ,nb_con, '\nnb_tag : ',nb_tag , '\nnb_nme : ',nb_nme , '\nnb_raw : ',nb_raw ,'\nnb_svp : ', nb_svp,'\nnb_dep : ',nb_dep)
    

    return d_param,d_power,d_traj
    


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
            decode_NME0(data)
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
    # Affiche le nom du fichier traite et le nombre de trames qu'il contient
    print('\nFichier : ',f.name)
    print('nb_tot : ',nb_tot,'\nnb_con : ' ,nb_con, '\nnb_tag : ',nb_tag , '\nnb_nme : ',nb_nme , '\nnb_raw : ',nb_raw ,'\nnb_svp : ', nb_svp,'\nnb_dep : ',nb_dep)
    
    return d_out
    

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
        Save = check_FileExists(outpath + fic_h5_data)
                
        if Save : # Sauvegarde
            # Creation d'un fichier de sortie h5
            store = pandas.HDFStore(outpath + fic_h5_data)
            store['data'] = d_power[ligne]
            store['trajectoire'] = d_traj[ligne]
            store['param'] = d_param[ligne]
            store.close()

    return None



def runDECODEandSAVE_RAWfiles(filesRAW_to_read,out_path,channels,survey_date,range_detection,depth_max_toSave):
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
    survey_date : datetime
        date a laquelle a ete realisee le leve (jour), par ex : dt.datetime(year=2020,month=10,day=7,hour = 0,minute = 0,second = 0)
    range_detection : list of int
        intervalle de profondeur utilise pour la detection du fond, par ex : [5,100]
    depth_max_toSave : int
        profondeur seuil pour la sauvegarde des donnees, ne pas sauvegarder si la profondeur est superieure au seuil

    """
    for channel in channels : # on parcout les canaux 
        for file in filesRAW_to_read : # on parcourt les fichiers de donnees .raw
            line = os.path.basename(file)[:5]
            print('-> Lecture du fichier RAW, Ligne : '+line+' Canal : '+str(channel))
            # Ouverture du fichier
            f = open(file, 'rb')
            # lecture et remplissage de dictionnaires :
            d_power,d_param,d_traj = read_RAWfile(f,line,channel,survey_date,range_detection,depth_max_toSave)
            print('Lecture achevee')
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
    
    # Variables 
    # Date du leve /!\ a modifier 07/10/2020 ou 23/10/2020   ->>> A SPECIFIER
    survey_date = dt.datetime(year=2020,month=10,day=7,hour = 0,minute = 0,second = 0)
    channels = [1,2] # canaux à lire {1:38kHz ; 2:200kHz}   ->>> A SPECIFIER
    range_detection = [5,100] # intervalle de profondeur pour la recherche du fond (en m)
    depth_max_toSave = 100 # profondeur max sauvegardee dans les fichiers h5 (en m)
      
    # Lecture et Sauvegarde des fichiers .RAW
    runDECODEandSAVE_RAWfiles(filesRAW_to_read,out_path,channels,survey_date,range_detection,depth_max_toSave)
    
    # Lecture et Sauvegarde des fichiers .OUT
    runDECODEandSAVE_OUTfiles(filesOUT_to_read,out_path)
    
    # Affichage du temps de calcul
    t_end = time.time() # Fin du temps de calcul
    print('\nCalculation time : ',round((t_end-t_start)/60),'min')