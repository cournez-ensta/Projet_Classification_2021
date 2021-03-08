#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Auteur : Aelaig COURNEZ - Flora GUES - Yann LAMBRECHTS - Romain SAFRAN

# Librairies importee
import numpy as np
import pandas
from scipy.stats import linregress
from scipy.spatial.transform import Rotation as R
from matplotlib.colors import ListedColormap
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from shapely.geometry import Polygon
import glob
import os
import rasterio
# Autres codes python
from colormap import custom_cm


#--------------------------------------------------------------------------------#
#                      ANALYSE DES DONNEES EA400                                 #
#                                                                                #
#   Ce code est compose d'un certain nombre de fonctions permettant de           #
#   traiter les donnees issues des acquisitions EA400 et d'afficher les          #
#   graphes utiles dans le cadre de notre projet "Classification des fonds       #
#   sous-marins par sondeur monofaisceau.                                        #
#--------------------------------------------------------------------------------#



#-------- FONCTION PERMETTANT DE CHARGER LES DONNEES H5 --------


def load_data(files):
    """
    Cette fonction permet de charger les donnees h5 de l'ensemble des fichiers dans une unqique base de donnees : d .

    Parametres
    ----------
    files : list of string
        chemin vers les fichiers .h5 a traiter

    Sortie
    -------
    d : dictionary
        base de donnees complete - toutes les lignes de leve d[line] - toutes les donnees d[line]['param'] ; d[line]['data'] ; d[line]['trajectoire']

    """
    d = {} # ce dictionnaire contiendra l'ensemble de la base de donnee contenue dans les differents fichiers .h5
    
    for f in files:
        line = os.path.basename(f)[:5]
        
        if line not in d:
            d[line] = {}
        # - Sauvegarde des 3 DataFrame dans le dictionnaire d - #
        d[line]['data'] = pandas.read_hdf(f,key = 'data')
        d[line]['trajectoire'] = pandas.read_hdf(f,key = 'trajectoire')
        d[line]['param'] = pandas.read_hdf(f,key = 'param') 
   
    return d



#------------- FONCTIONS D'AFFICHAGE -------------

def plotPing(d,line,title_str):
    """
    Cette fonction permet d'afficher la puissance maximale recue pour un ping
    on affiche la puissance associee au ping qui recoit le maximum de puissance 
    pour verifier qu'il n'y a pas de saturation.
    /!\ on visualise uniquement la portion qui permet de detecter le fond
    dans intervalle [DepthMinDetect,DepthMaxDetect]

    Parametres
    ----------
    d : dictionary
        base de donnees
    line : string
        identifiant de la ligne de leve, par ex : 'L0006'
    title_str : string
        titre de la figure affichee

    """
    # Recuperation des donnees et variables
    minDetect,maxDetect = float(d[line]['param'].loc[:,'DepthMinDetect']) , float(d[line]['param'].loc[:,'DepthMaxDetect'])
    Power = d[line]['data'].loc[:,'PowerDetectInterval']
    Power_ping_max = np.amax(Power,axis=0)
    len_power = len(Power_ping_max)
    depth = minDetect+float(d[line]['param'].loc[:,'SampleInterval']) * float(d[line]['param'].loc[:,'SoundVelocity'])/2*np.arange(len_power)
    
    # Affichage
    fig, ax = plt.subplots()
    plt.plot(depth,Power_ping_max)
    plt.xlim([0,maxDetect])
    plt.xlabel('Profondeur [m]')
    plt.ylabel('Puissance [db]')
    plt.title(title_str)
    return None


def plotEchogram(d,line,prof_display,title_str):
    """
    Cette fonction permet d'afficher l'echogramme d'une ligne de leve

    Parametres
    ----------
    d : dictionary
        base de donnees
    line : string
        identifiant de la ligne de leve, par ex : 'L0006'
    prof_display : int
        profondeur d'affichage maximale
    title_str : string
        titre de la figure affichee

    """
    # Recuperation des donnees utiles
    Time = d[line]['data'].loc[:,'DateTime']
    Power = d[line]['data'].loc[:,'Power']
    # Selection des donnees jusqu'a la profondeur specifiee
    ind_display = round( 2*prof_display / (float(d[line]['param'].loc[:,'SampleInterval']) * float(d[line]['param'].loc[:,'SoundVelocity'])))
    Power = np.array([np.array(li[:ind_display]) for li in Power]).T
    Depth = d[line]['data'].loc[:,'Depth']
    # Variables
    mi,ma = np.min(Power) ,  np.max(Power) # puissance min et max pour la colormap
    t_mi , t_ma = min(Time) , max(Time) # temps min et max pour la legende x
    x_lims = mdates.date2num([t_mi,t_ma]) # conversion en dates matplotlib
    
    # Affichage de l'echogramme des puissances
    fig, ax = plt.subplots()
    plt.imshow(Power, aspect='auto',extent=[x_lims[0],x_lims[1],prof_display,0],cmap=custom_cm(), vmin=mi*0.75,vmax=-abs(ma)*1.4)
    
    # Affichage de la detection du fond
    x=np.arange(t_mi,t_ma,(t_ma-t_mi)/(len(Depth)-1))
    plt.plot(x,Depth,c='black') 
    
    # Gestion de l'affichage de la date
    ax.xaxis_date() #Le format des abscisse est la date
    date_format = mdates.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_format)   #Applique le format %H:%M:%S
    fig.autofmt_xdate() #Dates affichees en diagonale
    
    # Affichage des legendes
    plt.title(title_str)
    ax.set_ylim(prof_display)
    plt.xlabel('Time')
    plt.ylabel('Depth [m]')
    cbar = plt.colorbar()
    cbar.set_label('[dB]', rotation=90)
    return None


def plotMap(d,line,value,value_str,title_str,cmap):
    """
    Cette fonction permet de tracer une carte X,Y avec value la grandeur en couleur
    à specifier en entree ex: 'PowerMax' un attribut de la base de donnees d[line]['data']

    Parametres
    ----------
    d : dictionary
        base de donnees
    line : string
        identifiant de la ligne de leve, par ex : 'L0006'
    value : string
        attribut que l'on souhaite afficher en couleur sur la carte
    value_str : string
        texte de legende de la colorbar
    title_str : string
        titre de la figure affichee
    cmap : string
        colormap choisie

    """
    # Donnees a afficher
    x , y , v = d[line]['data'].loc[:,'X'] , d[line]['data'].loc[:,'Y'] ,d[line]['data'].loc[:,value]
    dx , dy = 140000 , 6830000 # Offset sur les coordonnes pour la legende
    x -= dx
    y -= dy
    # Affichage de la carte
    plt.figure()
    plt.grid()
    plt.scatter(x,y,c=v,cmap=cmap,marker='.')
    plt.colorbar(label=value_str)
    plt.axis('equal')
    plt.xlabel('x [m] + '+str(dx))
    plt.ylabel('y [m] + '+str(dy))
    plt.title(title_str)
    return None


def plotLineZone(d,lines,title_str):
    """
    Cette fonction permet d'afficher la cartographie des zones definies d'apres l'attribut 'Zone'

    Parametres
    ----------
    d : dictionary
        base de donnees
    lines : list of string
        liste des lignes a afficher
    title_str : string
        titre de la figure affichee

    """
    # code couleur associe aux zones d'etude
    colors = ['tab:blue','tab:orange','tab:green','tab:red','tab:purple'] 
    dic_color={0:'grey',1:'tab:blue',2:'tab:orange',3:'tab:green',4:'tab:red',5:'tab:purple'}
    cm = ListedColormap([dic_color[x] for x in dic_color.keys()])

    plt.figure(figsize=(8,5))
    # Donnees a afficher
    for line in lines :
        x , y , v = d[line]['data'].loc[:,'X'] , d[line]['data'].loc[:,'Y'] ,d[line]['data'].loc[:,'Zone'].astype(int)
        dx , dy = 140000 , 6820000 # Offset sur les coordonnes pour la legende
        x -= dx
        y -= dy
        plt.scatter(x,y,c=v,cmap=cm,marker='.')
        plt.clim(-0.5, 5.5)

    # Affichage de la carte
    cb = plt.colorbar(ticks=range(0, 6), label='Zone')
    cb.ax.tick_params(length=0)
    plt.xlabel('X [m] - 140000 Lambert 93')
    plt.ylabel('Y [m] - 682000 Lambert 93')
    plt.axis('equal')
    # definition des zones initiales
    zone1 = Polygon([[7932, 10864], [7826, 10989], [8120, 11205], [8214, 11077]])
    zone2 = Polygon([[8026, 10005], [7945, 10093], [8170, 10312], [8255, 10225]])
    zone3 = Polygon([[7591, 9582], [7512, 9661], [7741, 9883], [7819, 9805]])
    zone4 = Polygon([[7099, 9122], [7027, 9206], [7227, 9382], [7299, 9303]])
    zone5 = Polygon([[6456, 10591], [6434, 10713], [6726, 10760], [6754, 10635 ]])
    zonesold = [zone1,zone2,zone3,zone4,zone5]
    i=0
    for zone in zonesold:
        x,y = zone.exterior.xy
        plt.plot(x,y,linestyle='-',c=colors[i])
        i+=1
        
    # definition des zones reduites
    # zone1 = Polygon([[8111, 11022], [8059, 11120], [8137, 11177], [8200, 11088]])
    zone1 = Polygon([[7909, 11018], [7970, 11058], [8045, 10968], [7981, 10911]])
    zone2 = Polygon([[8097, 10111], [8039, 10173], [8119, 10245], [8173, 10177]])
    zone3 = Polygon([[7665, 9667], [7586, 9740], [7663, 9810], [7727, 9746]])
    zone4 = Polygon([[7197, 9228], [7130, 9306], [7200, 9366], [7258, 9301]])
    zone5 = Polygon([[6527, 10611], [6510, 10712], [6694, 10745], [6723, 10635]])
    
    zonesnew = [zone1,zone2,zone3,zone4,zone5]
    i=0
    for zone in zonesnew:
        x,y = zone.exterior.xy
        plt.plot(x,y,linestyle='-')
        i+=1
        
    prelev = pandas.read_csv('Coordonnees_prelevements.csv')
    plt.scatter(prelev['X'].values-140000,prelev['Y'].values-6820000,marker='+',c='k',label='prélèvements')
    plt.legend()
    plt.title(title_str)
    return None



def plotBeamMap(d,lines,title_str,value=None,value_str=None,cmap=None,PosNavire=True):
    """
    Cette fonction permet d'afficher une cartographie des valeurs des attributs avec les positions des sondes calculees grace a computeCoordsBeam.

    Parametres
    ----------
    d : dictionary
        base de donnees
    lines : list of string
        liste des lignes a afficher
    title_str : string
        titre de la figure affichee
    value : string, optional
        attribut a afficher en couleur. The default is None.
    value_str : string, optional
        texte de la legende associe a la colorbar. The default is None.
    cmap : string, optional
        colormap choisie. The default is None.
    PosNavire : boolean, optional
        affichage ou non des positions du navire (True=affichage). The default is True.

    """
    cmap = matplotlib.cm.get_cmap('plasma')
    plt.figure()
    i=-0.5
    for line in lines : 
        i+=1
        
        x_body , y_body = d[line]['data'].loc[:,'X'] , d[line]['data'].loc[:,'Y']
        x_beam , y_beam = d[line]['data'].loc[:,'X_Beam'] , d[line]['data'].loc[:,'Y_Beam']
        dx , dy = 140000 , 6830000 # Offset sur les coordonnes pour la legende
        x_body -= dx
        y_body -= dy
        x_beam -= dx
        y_beam -= dy
        angle = d[line]['data'].loc[:,'Angle'][0]
        # affichage des positions du navire
        if PosNavire :
            plt.scatter(x_body[::10],y_body[::10],marker='.',s=5,label='Navire '+str(angle)+'°',color=cmap(i/5),alpha=0.5)
        # affichage des valeurs de l'attribut si value != None
        if value==None :
            plt.scatter(x_beam,y_beam,marker='.',label='Sonde '+str(angle)+'°',color=cmap(i/5))
        else : 
            v = d[line]['data'].loc[:,value]
            plt.scatter(x_beam,y_beam,c=v,cmap=cmap,marker='.')
            plt.clim(-35,0)
            
    # affichage de la figure        
    plt.colorbar(label=value_str)
    plt.axis('equal')
    plt.xlabel('x [m] + '+str(dx))
    plt.ylabel('y [m] + '+str(dy))
    plt.title(title_str)
    plt.legend()
    return None


#------------- CALCUL DE L'ANGLE D'INCIDENCE ------------- 

def computeCoordsBeam(d,bdl,pt,a_ouv):
    """
    Cette fonction permet de calculer les coordonnees precises de la tache insonifiee
    - coordonnees du centre
    - et coordonnees des extremites de la tache insonifiee selon l'axe transversal au navire

    Parametres
    ----------
    d : dictionary
        base de donnees
    bdl : list of float
        bras de levier x,y,z
    pt : list of float
        patch-test x,y,z
    a_ouv : float
        angle d'ouverture en degre

    Sortie
    -------
    d : dictionary
        base de donnees completee des attributs : X_Beam, Y_Beam, X_closeBeam, Y_closeBeam, X_farBeam, Y_farBeam

    """

    for line in d :
        # recuperation des donnees utiles
        data = d[line]['data']
        x_ins = data['X']
        y_ins = data['Y']
        z_ins = data['Height']
        depth = data['Depth']
        pitch = data['Pitch']
        roll  = data['Roll']
        yaw   = data['Gyro']
        a_dep = data['Angle'][0] # angle de depointage
        a_ape = a_ouv # angle d'ouverture
        nb_ping = data.shape[0]
        #Bras de levier du monofaisceau
        PSBES = np.array([bdl[2],bdl[1],bdl[0]])
        PatchTest = np.array([pt[2],pt[1],pt[0]])
    
        #Tableau vide pour position des sondes
        pos_sond = np.zeros((nb_ping,3))
        pos_sond_av = np.zeros((nb_ping,3))
        pos_sond_ap = np.zeros((nb_ping,3))
    
        for k in range(nb_ping):
    
            # coordonnées de la sonde dans le repére du monofaiseau
            m_sond = np.array([depth[k],0, 0])
    
            # Matrice de rotation our les angles d'installation du monofaisceau
            R_patch_test = R.from_euler('zyx', PatchTest, degrees=True)
    
            #Matrice de rotation avec les attitudes du bateau
            R_attitude = R.from_euler('zyx', [-(roll[k] + a_dep), pitch[k], -yaw[k]], degrees=True)
            #Matrice de rotation pour avoir position de la tache insonifiéé
            R_attitude_av = R.from_euler('zyx', [-(roll[k] + a_dep - a_ape/2), pitch[k], -yaw[k]], degrees=True)
            R_attitude_ap = R.from_euler('zyx', [-(roll[k] + a_dep + a_ape/2), pitch[k], -yaw[k]], degrees=True)
    
    
            #Coordonnées de l'INS
            zyx_ins = np.array([z_ins[k], y_ins[k], x_ins[k]])
    
            #Coordonnées des sondes
            pos_sond[k, :] = zyx_ins + R_attitude.apply(R_patch_test.apply(m_sond) + PSBES)
            #Coordonnées de la tache insonifiée
            pos_sond_av[k, :] = zyx_ins + R_attitude_av.apply(R_patch_test.apply(m_sond) + PSBES)
            pos_sond_ap[k, :] = zyx_ins + R_attitude_ap.apply(R_patch_test.apply(m_sond) + PSBES)
            
        data['X_Beam'] = pos_sond[:,2]
        data['Y_Beam'] = pos_sond[:,1]
        data['X_closeBeam'] = pos_sond_av[:,2]
        data['Y_closeBeam'] = pos_sond_av[:,1]
        data['X_farBeam'] = pos_sond_ap[:,2]
        data['Y_farBeam'] = pos_sond_ap[:,1]
        
        d[line]['data'] = data
    return d


def computeIncidenceAngle(d,d_mnt):
    """
    Cette fonction permet de calculer l'angle d'incidence du faisceau sur le fond à partir de la bathymetrie
    et de la position de la tache insonifiee

    Parametres
    ----------
    d : dictionary
        base de donnees
    d_mnt : dictionary
        dictionnaire associant a chaque zone, le chemin vers le MNT correspondant a la zone

    Sortie
    -------
    d : dictionary
        base de donnees complete avec l'attribut 'IncidenceAngle'

    """

    for line in d :
        data = d[line]['data']
        zone = int(max(data['Zone']))
        # ouverture du MNT
        mnt = rasterio.open(d_mnt[zone])
        bande_1 = mnt.read(1)
        
        nb_ping = data.shape[0]
        angle_i = np.zeros(nb_ping)
        
        X_av = data['X_closeBeam']
        Y_av = data['Y_closeBeam']
        X_ap = data['X_farBeam']
        Y_ap = data['Y_farBeam']
        roll = data['Roll']
        a_dep = data['Angle'][0]
    
        for k in range(nb_ping):
            try :
                row_av, col_av = mnt.index(X_av[k],Y_av[k])
                row_ap, col_ap = mnt.index(X_ap[k],Y_ap[k])
                # recuperer l'altitude du point
                z_av = bande_1[row_av, col_av]
                z_ap = bande_1[row_ap, col_ap]
                # calcul de la pente
                longueur_pente = np.sqrt((X_ap[k]-X_av[k])**2 + (Y_ap[k]-Y_av[k])**2)
                denivele = z_ap - z_av
        
                p = np.arcsin(denivele/longueur_pente)*180/np.pi
                phi = a_dep - roll[k]
                # calcul de l'angle d'incidence
                angle_i[k] = 90 - phi + p
            except :
                angle_i[k] = np.NaN
        
        data['IncidenceAngle'] = angle_i
        d[line]['data'] = data
    return d


#------------- CALCUL DE BS -------------

def compute_BS(d):
    """
    Cette fonction permet de calculer l'indice de retrodiffusion (BS) de chaque ping

    Parametres
    ----------
    d : dictionary
        base de donnees

    Sortie
    -------
    d : dictionary
        base de donnees completee avec l'attribut 'BS_calc'

    """

    for line in d :
        # Puissance max recue
        Pr_max = d[line]['data'].loc[:,'PowerMax']
    
        # Puissance emise
        Pe = d[line]['data'].loc[:,'TransmitPower'].astype(float)
    
        # Range
        r = d[line]['data'].loc[:,'Depth'].astype(float)
        
        # Angle d'incidence
        angle_i = d[line]['data'].loc[:, 'IncidenceAngle'].astype(float)
    
        # Coefficient d'absorption
        alpha = float(d[line]['param'].loc[:,'AbsorptionCoefficient'])
        
        # Celerite
        c = float(d[line]['param'].loc[:,'SoundVelocity'])
        
        # Longueur d'impulsion
        tpulse = float(d[line]['param'].loc[:,'PulseLength'])
        
        # Longueur d'onde
        lambd = float(d[line]['param'].loc[:,'SoundVelocity']/d[line]['param'].loc[:,'Frequency'])
        
        
        if (float(d[line]['param'].loc[:,'Frequency'])==38000):
            # Gain de traitement
            Gain = float(d[line]['param'].loc[:,'Gain_38'])
            # Angle solide equivalent 
            psi = float(d[line]['param'].loc[:,'EquivalentBeamAngle_38'])
        else :
            Gain = float(d[line]['param'].loc[:,'Gain_200'])
            psi = float(d[line]['param'].loc[:,'EquivalentBeamAngle_200'])
        
        # Calcul du BS nadir _ version 1
        # BS_nadir =  Pr_max - 10*np.log10(Pe) + 20*np.log10(r) + 2*alpha*r - 10*np.log10(lambd**2/(16*(np.pi)**2)) - psi - 2*Gain
        
        # Calcul du BS nadir _ version 2
        # Aire au nadir
        Aire_nadir = 10**(psi/10) * r**2
        # Aire en incidence
        Aire_angle = ( (c*tpulse*r) / (2*np.sin(angle_i/180*np.pi)) ) * np.sqrt( (4* 10**(psi/10)) /np.pi )
        Aire = np.min( np.vstack((Aire_nadir , Aire_angle)) ,axis=0)
    
        # Calcul du BS
        BS =  Pr_max - 10*np.log10(Pe) + 40*np.log10(r) + 2*alpha*r - 10*np.log10(lambd**2/(16*(np.pi)**2)) - 10*np.log10( Aire ) - 2 * Gain

        # Sauvegarde du BS calcule dans le dictionnaire d
        d[line]['data'].loc[:,'BS_calc'] = BS
    return d


def plotCompareBS(d,line,BS_Kongsberg,title_str):
    """
    Cette fonction permet d'afficher la comparaison entre BS_calcule et BS_Kongsberg

    Parametres
    ----------
    d : dictionary
        base de donnees
    line : string
        identifiant de la ligne de leve
    BS_Kongsberg : dictionary
        dictionnaire comprenant les donnees de BS calculees par Konberg
    title_str : string
        titre de la figure affichee

    """
    # Recuperation des donnees
    Time = d[line]['data'].loc[:,'DateTime']
    BS = d[line]['data'].loc[:,'BS_calc'].astype(float)
    BS_Kongsberg = BS_Kongsberg['BS_38'].astype(float)
    
    if (BS.shape==BS_Kongsberg.shape):
        
        # Affichage des courbes de BS en fonction du temps
        fig, ax = plt.subplots( figsize=(15,5))
        plt.subplot(121)
        plt.plot(Time,BS, label='Computed BS')
        plt.plot(Time,BS_Kongsberg, label='Kongsberg BS')
        # Gestion de l'affichage de la date
        ax.xaxis_date() #Le format des abscisse est la date
        date_format = mdates.DateFormatter('%H:%M:%S')
        ax.xaxis.set_major_formatter(date_format)   #Applique le format %H:%M:%S
        fig.autofmt_xdate() #Dates affichees en diagonale
        # Affichage des legendes
        plt.legend()
        plt.xlabel('Time')
        plt.ylabel('BS [dB]')
        
        # Affichage de la courbe de correlation du BS
        plt.subplot(122)
        # Calcul de la regression lineaire
        a,b,r,p,std = linregress(BS_Kongsberg,BS)
        plt.scatter(BS_Kongsberg,BS,marker='.')
        minBS, maxBS = min(BS_Kongsberg) , max(BS_Kongsberg)
        plt.plot([minBS,maxBS],[a*minBS+b,a*maxBS+b],label='a='+"{:.3f}".format(a)+'; b='+"{:.3f}".format(b)+'\ncorrelation='+"{:.3f}".format(r),c='r')
        plt.xlabel('Kongsberg BS [dB]')
        plt.ylabel('Computed BS [dB]')
        plt.legend()
        plt.suptitle(title_str)
        
    else : 
        print('Erreur : le nombre de valeur est different entre les 2 listes de BS')
    
    return None


#------------- SAUVEGARDE DONNEES -------------

def saveData(d,lines,zone,filename):
    """
    Cette fonction permet de sauvegarder en csv une base de donnees synthetique comprenant 
    les attributs : ['Line','X_Beam','Y_Beam','BS_calc','IncidenceAngle'] sur une zone donnee.

    Parametres
    ----------
    d : dictionary
        base de donnees
    lines : list of string
        liste des lignes de leve a sauvegarder
    zone : int
        identifiant de la zone d'interet
    filename : string
        chemin vers le fichier a exporter (repertoire+nom du fichier a exporter)

    """
    # traitements des donnees
    for line in lines:
        d = computeCoordsBeam(d,line,bras_levier,patch_test) # calcul du positionnement des sondes
        d = computeIncidenceAngle(d,line,d_mnt,zone) # calcul de l'angle d'incidence
        d = compute_BS(d,line) # calcul de l'indice de retrodiffusion
    
    d_all = pandas.DataFrame()
    for line in d :
        # selection des donnees a sauvegarder
        data = d[line]['data']
        data_zone = data.loc[data['Zone']==zone]
        d_save = data_zone[['X_Beam','Y_Beam','BS_calc','IncidenceAngle']]
        d_save.loc[:, 'Line'] = line
        d_save = d_save[['Line','X_Beam','Y_Beam','BS_calc','IncidenceAngle']]
        d_all = d_all.append(d_save,ignore_index=True) # on concatene les donnees des differentes lignes de leve
    # sauvegarde des donnees
    d_all.to_csv(filename)
    return None

    
if __name__=='__main__':
    
    plt.close('all') # Fermer toutes les figures encore ouvertes
    
    #----- CHEMINS VERS LES REPERTOIRES -----
    
    dir_path = './fic_h5/' # repertoire d'entree contenant les fichiers h5   ->>> A SPECIFIER
    
    files38_h5 = glob.glob(dir_path+'*_38kHz_data.h5') # Ensemble des fichiers h5 à 38kHz à traiter (chemins)
    files200_h5 = glob.glob(dir_path+'*_200kHz_data.h5') # Ensemble des fichiers h5 à 200kHz à traiter (chemins)
       
    # Chemins vers les MNT pour chaque zone d'etude
    d_mnt = {1:'./MNT/MNT_Zone1_07102020_L93.tif',2:'./MNT/MNT_Zone2_07102020_L93.tif',3:'./MNT/MNT_Zone2_07102020_L93.tif',4:'./MNT/MNT_Zone2_07102020_L93.tif',5:'./MNT/MNT_Zone3_07102020_L93.tif'}
        
    #----- CHARGEMENT DE LA BASE DE DONNEES -----
    
    d = load_data(files38_h5) # Chargement des donnees 38kHz
    
    #----- VARIABLES ------
    bras_levier = [1.2565,-1.21,-1.881] # Bras de levier x,y,z
    patch_test  = [0,0,0] # Patch test x,y,z
    a_ouv_38 = 21 # 21° pour le 38kHz 
    a_ouv_200 = 7 # 7° pour le 200kHz 
    
    #----- IMPORT DES DONNEES KONGSBERG -----

    # filepath = dir_path+'L0007_ref.txt'
    # L0007_Kongsberg = pandas.read_csv(filepath,sep=' ') # le premier fichier ref ici L0007
    # Kongsberg = L0007_Kongsberg[['DateTime','BS_38']]
 
    #----- TRAITEMENTS -----
    
    # d = computeCoordsBeam(d,bras_levier,patch_test, a_ouv_38)
    # d = computeIncidenceAngle(d,d_mnt)
    # d = compute_BS(d)
    
    #----- AFFICHAGES -----
    
    # # Affichage d'un echogramme
    # line = 'L0024'
    # profondeur_affichage = 50 
    # title_echogram = line + " - Volumic backscatter - 38 kHz"
    # plotEchogram(d,line,profondeur_affichage,title_echogram)
    
    # # Comparaison des BS
    # plotCompareBS(d,line,Kongsberg,'BS Comparison')

    # # Affichage d'une carte
    # power = 'BS_calc' # attribut dans le dictionnaire 'data' = ce qu'on veut afficher comme valeur en couleur
    # plotMap(d,'L0019',power,'Power (en dB)','Power','plasma')

    
    plt.show()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    