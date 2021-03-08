#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Librairies importee
import numpy as np
import pandas
from scipy.stats import linregress
import scipy.stats
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import glob
import os
import datetime as dt
#import rasterio
#from rasterio.plot import show
from shapely.geometry import  Point, Polygon
# Autres codes python
from colormap import custom_cm
import statistics
import math
import matplotlib

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
    ''' Cette fonction permet de charger les donnees h5 de l'ensemble des fichiers dans une unqique base de donnees d
    '''
    d = {} # ce dictionnaire contiendra l'ensemble de la base de donnée contenue dans les differents fichiers .h5
    
    for f in files:
        line = os.path.basename(f)[:5]
        
        if line not in d:
            d[line] = {}
        # - Sauvegarde des 3 DataFrame dans le dictionnaire d - #
        d[line]['data'] = pandas.read_hdf(f,key = 'data')
        d[line]['trajectoire'] = pandas.read_hdf(f,key = 'trajectoire')
        d[line]['param'] = pandas.read_hdf(f,key = 'param') 
   
    return d

#------------- FONCTIONS INTERMEDIAIRES -------------
def find_nearest(array, value):
    idx = (np.abs(array - value)).argmin()
    return idx


def dist(xa,ya,xb,yb):
    dist = np.sqrt((xa-xb)**2 + (ya - yb)**2)
    return dist

def compute_sigma(array):
    nb = array.shape[0]
    sigma = round(np.sqrt((1/(2*nb))*np.nansum(array**2)),4)
    sigma = round(20*np.log10(sigma),4)
    return sigma
#------------- VALIDATION DU CALCUL DE BS -------------

def compute_BS(d,line):
    """ Cette fonction permet de calculer le BS
    """
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
    BS =  Pr_max - 10*np.log10(Pe) + 40*np.log10(r) + 2*alpha*r - 10*np.log10(lambd**2/(16*(np.pi)**2)) - 10*np.log10( Aire_nadir ) - 2 * Gain
    
    # Sauvegarde du BS calcule dans le dictionnaire d
    d[line]['data'].loc[:,'BS_calc'] = BS
    return d


def plotCompareBS(d,line,BS_Kongsberg,title_str):
    """ Cette fonction permet d'afficher la comparaison entre BS_calculé et BS_Kongsberg
    """
    # Recuperation des donnees
    Time = d[line]['data'].loc[:,'DateTime']
    Pings = d[line]['data'].index
    BS = d[line]['data'].loc[:,'BS_calc'].astype(float)
    if freq == '38 kHz':
        BS_Kongsberg = BS_Kongsberg['BS_38'].astype(float)
    if freq == '200 kHz':
        BS_Kongsberg = BS_Kongsberg['BS_200'].astype(float)   
        
    Prof_kong = depth_kongsberg.values
    Prof = d[line]['data'].loc[:,'Depth']
    diff_BS = BS - BS_Kongsberg
        
    
    if (BS.shape==BS_Kongsberg.shape):
        
        
        diff_BS = BS - BS_Kongsberg
        diff_prof = Prof - Prof_kong
        mean_diff_BS = np.mean(diff_BS)
        
        outlier_ping = []
        outlier_prof = []
        outlier_value = []
        liste_pente = []
        
        for k in range(diff_BS.shape[0]):
            if np.abs(diff_BS[k]) >= 1:
                outlier_ping.append(k)
                outlier_value.append(diff_BS[k])
                diff_BS[k] = np.nan
                outlier_prof.append(Prof[k])
            else :
                if k >= 5 :
                    None
        
        # Affichage des courbes de BS en fonction du temps
        fig, ax = plt.subplots( figsize=(15,5))
        plt.subplot(221)
        plt.plot(Pings,BS, label='BS Calculé')
        plt.plot(Pings,BS_Kongsberg, label='BS Kongsberg')
        plt.grid()
        # Gestion de l'affichage de la date
        ax.xaxis_date() #Le format des abscisse est la date
        date_format = mdates.DateFormatter('%H:%M:%S')
        ax.xaxis.set_major_formatter(date_format)   #Applique le format %H:%M:%S
        fig.autofmt_xdate() #Dates affichees en diagonale
        # Affichage des legendes
        plt.legend()
        plt.xlabel('Pings')
        plt.ylabel('BS [dB]')
        
        # Affichage de la courbe de correlation du BS
        plt.subplot(222)
        plt.grid()
        # Calcul de la regression lineaire
        mask = ~np.isnan(BS_Kongsberg) & ~np.isnan(BS)
        a,b,r,p,std = linregress(BS_Kongsberg[mask],BS[mask])
        # print(a,b,r,p,std)
        plt.scatter(BS_Kongsberg,BS,marker='.')
        minBS, maxBS = np.nanmin(BS_Kongsberg) , np.nanmax(BS_Kongsberg)
        plt.plot([minBS,maxBS],[minBS,maxBS],color = 'black',linewidth=1.1,label = 'y = x')
        plt.plot([minBS,maxBS],[a*minBS+b,a*maxBS+b],'--',linewidth=0.8,label='a='+"{:.3f}".format(a)+'; b='+"{:.3f}".format(b)+'\ncorrelation='+"{:.3f}".format(r),c='r')
        plt.xlabel('Kongsberg BS [dB]')
        plt.ylabel('BS calculé [dB]')
        plt.legend()
        
        
        plt.subplot(223)
        plt.scatter(-Prof,diff_BS,color = 'red',s = 8,marker='.',label = 'Ecart BS calculé / BS Kongsberg\nmean = '+str(round(mean_diff_BS,3))+ ' dB')
        plt.xlabel('Profondeur [m]')
        plt.ylabel('BS_calculé - BS_Kongsberg [dB]')
        plt.grid()
        
        plt.legend()
        
        plt.subplot(224)
        plt.plot(Pings,-Prof,color = 'blue',label = 'Profondeur calculée sur maximum de puissance')
        plt.xlabel('Pings')
        plt.ylabel('Profondeur [m]')
        plt.grid()
        plt.legend()
        title_str = line + ' - Comparaison BS calculé - BS Kongsberg - Hypothèse nadir'
        plt.suptitle(title_str)
        plt.show()
        
        
        plt.figure()
        plt.suptitle(line + ' - Comparaison profondeur Kongsberg - Profondeur calculée')
        plt.subplot(211)
        plt.scatter(Pings,diff_prof,marker = '.',color = 'blue',label = 'Ecart : Profondeur calculé sur max de puissance reçue - Profondeur Kongsberg [m]\n'+'Mean : '+str(round(np.mean(diff_prof),2))+' m')
        plt.axhline(0,0,Pings[-1],color = 'black',linewidth=1.1)
        plt.ylabel('Différence [m]')
      
        plt.grid()
        plt.legend()
        plt.subplot(212)
        plt.scatter(Pings,diff_BS,color = 'red',s = 8,marker='.',label = 'Ecart BS calculé / BS Kongsberg\nmean = '+str(round(mean_diff_BS,3))+ ' dB')
        plt.xlabel('Pings')
        plt.ylabel('BS_calculé - BS_Kongsberg [dB]')
        plt.grid()
        plt.legend()
        plt.show()
    else : 
        print('Erreur : le nombre de valeur est different entre les 2 listes de BS')
    
    
    
    return None

    

def classif_BS(d,freq,empreinte,BS_ref_with_circle,BS_ref_with_zone,print_fig):
    '''
    

    Parameters
    ----------
    d : Dictionnaire
        Contient l'ensemble des données générées par un autre code,
        extraites des fichiers de données brutes du sondeur monofaisceau EA400'
    freq : Str,
        Fréquence étudiée et son unité (e.g : freq = '38 kHz')
        
    empreinte : Float
        Rayon de recherche des pings à séléctionner autour des points contenus
        dans 'd_prelev', pour étudier la distribution des valeurs de BS
        de chaque zone
    BS_ref_with_circle : Booléen,
        Choisir les ping par des cercles de rayon empreinte centrés sur les 
        points de d_prelev, pour étudier la distribution des valeurs de chaque zone
    BS_ref_with_zone : Booléen,
        Choisir tous les ping de chaque zone, pour analyser la distribution
        des valeurs de BS de chaque zone
    print_fig : Booléen
        Afficher les histograme de valeurs de BS par zone

    Returns
    -------
    d_BS_ref : Dictionnaire
        Contient les valeurs de BS par zone, à analyser par le moyen d'autres fonctions'

    '''
    
    
    d_BS_ref = {}
    ### On rempli le dictionnaire contenant seulement les valeurs de BS 
    # par ligne et par zone
    
    
    
    for k in range(len(list_zone)):
        zone = list_zone[k]
        sedi = list_sedi_zone[k]
        couleur = list_color_zone[k]
        
        if zone not in d_BS_ref:
            d_BS_ref[zone] = {}
            d_BS_ref[zone]['BS'] = []
            d_BS_ref[zone]['lines'] = []
            d_BS_ref[zone]['color'] = couleur
            
            # ajout type de sédiment à chaque zone de ref
            d_BS_ref[zone]['sedi'] = sedi
        
        for line in d:
            for ping in d[line]['data'].index:
                
                # WARNING #
                ''' ne prendre que les pings les plus proche des prélèvements !
                '''
                
                
                if not math.isnan(d[line]['data'].loc[ping,'Zone']):
                    
                    
                    BS = d[line]['data'].loc[ping,'BS_calc']
                    BS = 10**(BS/20)
                    
                    Zone_ = int(d[line]['data'].loc[ping,'Zone'])
                    Zone = 'Zone ' + str(Zone_)
                    
                    # on cherche toutes les valeurs de BS dans d qui correspondent à la zone 'zone'
                    # on crée un parame 'Zone', que l'on fait corespondre à 'zone' ; on cherche également
                    # des sondes contenues dans le carré de côté empreinte centré sur le prélèvement 2 de
                    # chaque zone
                    # c'est une interpolation en fait :
                    
                    
                    if BS_ref_with_circle :
                        xbeam,ybeam = d[line]['data'].loc[ping,'X_Beam'],d[line]['data'].loc[ping,'Y_Beam']
                        cond = []
                        for prelev in d_prelev[zone]:
                            xp,yp = d_prelev[zone][prelev][0],d_prelev[zone][prelev][1]
                            dist_ = dist(xbeam,ybeam,xp,yp)
                            cond.append(dist_ < empreinte)
                        
                        cond_prelev = None
                        for k in range(len(cond)):
                            cond_prelev = cond_prelev or cond[k]
                        
                        
                        if cond_prelev :
                            
                            # print(Zone)
                            
                            if Zone == 'Zone 1':
                                if line == 'L0008':
                                    d_BS_ref[Zone]['BS'].append(BS)
                            # ajout valeur de BS correspondant à chaque zone de ref :
                            else :
                                d_BS_ref[Zone]['BS'].append(BS)
                    
                            # ajout chaque ligne dont proviennent les valeurs de BS par zone
                            if Zone == 'Zone 1':
                                if line == 'L0008' and line not in d_BS_ref[Zone]['lines']:
                                    d_BS_ref[Zone]['lines'].append(line)
                            else :
                                if line not in d_BS_ref[Zone]['lines']:
                      
                                    d_BS_ref[Zone]['lines'].append(line)
                                    
                    # cond = Zone == zone
                    if BS_ref_with_zone :
                    
                        if  Zone == zone :
                            if Zone == 'Zone 1':
                                if line == 'L0008':
                                    d_BS_ref[Zone]['BS'].append(BS)
                            # ajout valeur de BS correspondant à chaque zone de ref :
                            else :
                                # print(Zone)
                                d_BS_ref[Zone]['BS'].append(BS)
                    
                            # ajout chaque ligne dont proviennent les valeurs de BS par zone
                            if Zone == 'Zone 1':
                                if line == 'L0008' and line not in d_BS_ref[Zone]['lines']:
                                    d_BS_ref[Zone]['lines'].append(line)
                            else :
                                if line not in d_BS_ref[Zone]['lines']:
                      
                                    d_BS_ref[Zone]['lines'].append(line)
    
  
    # Affichage des histogramme de BS et fit lois de Rayleigh :
    
    for zone in d_BS_ref:
       
       
       
       
       sedi = d_BS_ref[zone]['sedi']
       title = sedi + ' - ' + zone + ' - ' + freq
       
       hist_to_analyse = d_BS_ref[zone]['BS']
       
       provenance_lines = d_BS_ref[zone]['lines']
       color_ = d_BS_ref[zone]['color']
       array_BS = np.array(hist_to_analyse)
       
       # distribution = scipy.stats.rayleigh
       # params = distribution.fit(array_BS)
       
       nb = len(hist_to_analyse)
       bins = facteur_bins
       
       # estimateur, maximum de vraissemblance lois de rayleigh : sqrt(1/2N sum 1 à N Xi**2)
       sigma = round(np.sqrt((1/(2*nb))*np.sum(array_BS**2)),4)
       
       # ar_BS_rayleigh = 20*np.log10(array_BS)
       
       # lois de rayleigh sur le maximum de vraissemblance :
       sigma2 = sigma ** 2
       x = np.linspace(np.nanmin(array_BS),np.nanmax(array_BS),100)
       x2 = x**2
       rayleigh_distribution = (x*np.exp(-x2/(2*sigma2)))/sigma2

       # indicateur statistique des valeurs de BS par zone
       std = round(np.std(20*np.log10(array_BS)),2)
       mean = round(np.mean(20*np.log10(array_BS)),2)
       
       # sigma in dB :
       sigma = round(20*np.log10(sigma),3)
       d_BS_ref[zone]['sigma'] = sigma
       
      
       
       label_ = 'Nb échantillon : ' + str(nb) + '\nStd : ' + str(std)+' dB'\
           + '\nMoyenne : ' + str(mean) +' dB'\
           + '\nProvenance : ' + str(provenance_lines[0])
        
      
       if print_fig :
           plt.figure()
           plt.title(title)
           plt.xlabel('BS [W]')
           plt.ylabel('Occurences %')
           plt.hist(array_BS,bins = bins,histtype = 'step', linewidth = 2, density = True, color = color_)
           plt.hist(array_BS,bins = bins,histtype = 'stepfilled', alpha = 0.5, linewidth = 5, density = True, color = color_,label = label_)
           plt.plot(x,rayleigh_distribution,color = 'black',label = 'Rayleigh : ' + '\n$\hat{\sigma}_'+zone[-1]+' = ' + str(sigma)+ ' $ dB')
           if zone == 'Zone 1':
               loc = 'upper left'
           else :
               loc = 'best'
           plt.legend(loc = loc)
           plt.grid()
    
           plt.show()
   
    return d_BS_ref

def par_zone_classif_BS(facteur_bins,zone_,d,freq,empreinte,BS_ref_with_circle,BS_ref_with_zone):
    '''

    Parameters
    ----------
    facteur_bins : Float,
        Nombre de bins à utiliser dans le calcul des histogrames
    zone_ : Str,
        Zone à analyser (cf. returns)
    d : Dictionnaire,
        Base de donnée chargées par la fonction load_data
    freq : Str,
        Fréquence à étudier (e.G : freq = '38 kHz')
        
    empreinte : Float
        Rayon de recherche des pings à séléctionner autour des points contenus
        dans 'd_prelev', pour étudier la distribution des valeurs de BS
        de chaque zone
    BS_ref_with_circle : Booléen,
        Choisir les ping par des cercles de rayon empreinte centrés sur les 
        points de d_prelev, pour étudier la distribution des valeurs de chaque zone
    BS_ref_with_zone : Booléen,
        Choisir tous les ping de chaque zone, pour analyser la distribution
        des valeurs de BS de chaque zone

    Returns
    -------
    Pour une zone, affiche un subplot de la distribution des valeurs des BS,
    et d'une autre figure générée par une autre fonction. Cf. main.

    '''
   
    
    for k in range(len(list_zone)):
        zone = list_zone[k]
        sedi = list_sedi_zone[k]
        
        
        if zone == zone_:
           
           
           plt.subplot(121)
           
               
           sedi = d_BS_ref[zone]['sedi']
           title = sedi + ' - ' + zone + ' - ' + freq
           
           hist_to_analyse = d_BS_ref[zone]['BS']
           
           provenance_lines = d_BS_ref[zone]['lines']
           color_ = d_BS_ref[zone]['color']
           array_BS = np.array(hist_to_analyse)
           
           # distribution = scipy.stats.rayleigh
           # params = distribution.fit(array_BS)
           
           nb = len(hist_to_analyse)
           bins = facteur_bins
           
           # estimateur, maximum de vraissemblance lois de rayleigh : sqrt(1/2N sum 1 à N Xi**2)
           sigma = round(np.sqrt((1/(2*nb))*np.sum(array_BS**2)),4)
           
           # ar_BS_rayleigh = 20*np.log10(array_BS)
           
           # lois de rayleigh sur le maximum de vraissemblance :
           sigma2 = sigma ** 2
           x = np.linspace(np.nanmin(array_BS),np.nanmax(array_BS),100)
           x2 = x**2
           rayleigh_distribution = (x*np.exp(-x2/(2*sigma2)))/sigma2
    
           # indicateur statistique des valeurs de BS par zone
           std = round(np.std(20*np.log10(array_BS)),2)
           mean = round(np.mean(20*np.log10(array_BS)),2)
           
           
           x_exp = np.linspace(np.min(array_BS),np.max(array_BS),array_BS.shape[0])
           x_exp2 = x_exp**2
           
         
           rayleigh_expected = (x_exp*np.exp(-x_exp2/(2*sigma2)))/sigma2
           
           
           hist_exp,edges_exp = np.histogram(rayleigh_expected,bins = bins)
           
           
           # sigma in dB :
           sigma__ = round(20*np.log10(sigma),3)
           d_BS_ref[zone]['sigma'] = sigma__
           
           sigma = sigma__
           label_ = 'Nb échantillon : ' + str(nb) + '\nStd : ' + str(std)+' dB'\
               + '\nMean : ' + str(mean) +' dB'\
               + '\nProvenance : ' + str(provenance_lines[0])
            
          
            
          
           plt.title(title)
           plt.xlabel('BS [W]')
           plt.ylabel('Occurences %')
           plt.hist(array_BS,bins = bins,histtype = 'step', linewidth = 2, density = True, color = color_)
           plt.hist(array_BS,bins = bins,histtype = 'stepfilled', alpha = 0.5, linewidth = 5, density = True, color = color_,label = label_)
           plt.plot(x,rayleigh_distribution,color = 'black',label = 'Rayleigh : '+ '$\hat{\sigma}_'+zone[-1]+'$ : ' + str(sigma)+' dB')
           plt.legend()
           plt.grid()
        
        
   
    return None



def classif_glissante_BS(d,nbping,sampling,d_BS_ref,print_fig):
    '''
    

    Parameters
    ----------
    d : Dictionanire,
        Base de donnée chargée par load_data
    nbping : Int,
        Nombre de pings séléctionnés pour le clacul d'une valeur de sigma 
        par fenêtre glissante, càd taille de la fenêtre en nombre de ping
    sampling : Int,
        Fréquence d'échantillonnage dans le calcul des valeurs de sigma
    d_BS_ref : Dictionnaire
        Valeurs de BS par zone : contient entre autre la valeur de sigma
        de référence pour chaque zone
    print_fig : Bool,
        Affiche toutes les figures 'valeurs de sigma par fenêtre glissante'
        de chaque zone

    Returns
    -------
    d_sigma : Dictionnaire
        Valeurs de sigma correspondant à chaque fenêtre, sur chaque ligne

    '''
    
    
    
    '''
    Remarque :
        
    nbping est la taille de la fenêtre glissante
    sampling est l'échantillonnage : on centrera la fenêtre sur des ping espacés de 'sampling'
        
    '''
    d_sigma = {}
    
    list_color_zone = ['tab:blue','tab:orange','tab:green','tab:red','tab:purple']
    
    for line in d:
        
        if line not in d_sigma:
            d_sigma[line] = pandas.DataFrame(columns=['Zone','X','Y','sigma'])
        
        centre = int(nbping/2)
        start = 0
        stop = nbping
        length = d[line]['data'].shape[0]
        s = centre
        
        
        for ping in d[line]['data'].index:
            
            if ping == s and stop <= length :
                
                ar_BS = np.array(d[line]['data'].loc[start:stop,'BS_calc'])
                ar_BS = 10**(ar_BS/20)
                # print(start, ' ', stop)
                sigma = compute_sigma(ar_BS)
                
                X = d[line]['data'].loc[s,'X_Beam']
                Y = d[line]['data'].loc[s,'Y_Beam']
                zone = d[line]['data'].loc[s,'Zone']
                
                # sauvegarde des valeurs pour chaque ping (echantillonnage définie par 'sampling')
                
                d_sigma[line].loc[ping,'Zone'] = zone
                d_sigma[line].loc[ping,'X'] = X
                d_sigma[line].loc[ping,'Y'] = Y
                d_sigma[line].loc[ping,'sigma'] = sigma
                
                s+=sampling
                centre+=sampling
                
                start = start + sampling
                stop = stop + sampling
        
        
        # zone1 = Polygon([[148111, 6831022], [148059, 6831120], [148137, 6831177], [148200, 6831088]])
        zone2 = Polygon([[148097, 6830111], [148039, 6830173], [148119, 6830245], [148173, 6830177]])
        zone3 = Polygon([[147665, 6829667], [147586, 6829740], [147663, 6829810], [147727, 6829746]])
        zone4 = Polygon([[147197, 6829228], [147130, 6829306], [147200, 6829366], [147258, 6829301]])
        zone5 = Polygon([[146527, 6830611], [146510, 6830712], [146694, 6830745], [146723, 6830635]])
        if compute_on_zone1bis :
            zone1 = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
        else :
            zone1 = Polygon([[148111, 6831022], [148059, 6831120], [148137, 6831177], [148200, 6831088]])
        # zone1bis = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
        
        
        
        
        if print_fig :
            
            plt.figure(figsize=(12, 7))
            
            plt.title(line + ' - ' + freq + ' - Sigma  - Calculés sur '+str(nbping) + ' pings via fenêtre glissante')
            
            if line == 'L0008':
                zone = 'Zone 1'
                if BS_ref_with_zone :
                    label_zone = '\nPings séléctionnés pour calculer Sigma_ref = ' + str(d_BS_ref[zone]['sigma']) + ' dB'
                else : 
                    label_zone = ' '
                x,y = zone1.exterior.xy
                plt.plot(x, y, color=list_color_zone[0],
                     linestyle = '--', zorder=2, label = zone + ' - ' + d_BS_ref[zone]['sedi'] + label_zone)
            
            if line == 'L0018':
                zone = 'Zone 4'
                if BS_ref_with_zone :
                    label_zone = '\nPings séléctionnés pour calculer Sigma_ref = ' + str(d_BS_ref[zone]['sigma']) + ' dB'
                else : 
                    label_zone = ' '
                x,y = zone4.exterior.xy
                plt.plot(x, y, color=list_color_zone[3],
                     linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
            
            if line == 'L0019':
                
                x,y = zone2.exterior.xy
                x_,y_ = zone3.exterior.xy
                zone = 'Zone 2'
                if BS_ref_with_zone :
                    label_zone = '\nPings séléctionnés pour calculer Sigma_ref = ' + str(d_BS_ref[zone]['sigma']) + ' dB'
                else : 
                    label_zone = ' '
                plt.plot(x, y, list_color_zone[1],
                     linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
                
                zone = 'Zone 3'
                if BS_ref_with_zone :
                    label_zone = '\nPings séléctionnés pour calculer Sigma_ref = ' + str(d_BS_ref[zone]['sigma']) + ' dB'
                else : 
                    label_zone = ' '
                    
                plt.plot(x_, y_, color=list_color_zone[2],
                     linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
            
            if line == 'L0024':
                
                zone = 'Zone 5'
                if BS_ref_with_zone :
                    label_zone = '\nPings séléctionnés pour calculer Sigma_ref = ' + str(d_BS_ref[zone]['sigma']) + ' dB'
                else : 
                    label_zone = ' '
                x,y = zone5.exterior.xy
                plt.plot(x, y, color=list_color_zone[4],
                     linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
            
            # affichage relatifs aux prélèvements :
            for zone in d_prelev:
                if line in d_BS_ref[zone]['lines']:
                    added = False
                    for prelev in d_prelev[zone]:
                        if not added :
                            labell = 'Prélèvements'
                        if added :
                            labell = None
                        added = True
                        
                        xp = d_prelev[zone][prelev][0]
                        yp = d_prelev[zone][prelev][1]
                        
                        plt.scatter(xp,yp,marker = '+',s=60,color = d_BS_ref[zone]['color'],label = labell)
                        
                        if BS_ref_with_circle :
                            theta = np.linspace(0, 2*np.pi, 100)
                            r = empreinte
                            x1 = r*np.cos(theta) + xp
                            x2 = r*np.sin(theta) + yp
                            if prelev == '3':
                                label = 'Pings séléctionnés pour calculer Sigma_ref = ' + str(d_BS_ref[zone]['sigma']) + ' dB'
                            else :
                                label = None
                            plt.plot(x1, x2,color = d_BS_ref[zone]['color'], linewidth = 0.8, linestyle = ':', label = label)
                        
            # Affichage des valeurs de sigma calculées sur moyenne glissante      
            sigma_values = d_sigma[line]['sigma'].values
            z = sigma_values
            X = d_sigma[line]['X'].values
            Y = d_sigma[line]['Y'].values
            sc = plt.scatter(X, Y, c=z, vmin=-15,vmax = -18, s=35, cmap='viridis')
            cbar = plt.colorbar(sc)
            cbar.set_label('Sigma en [dB] - Maximum de vraissemblance sur la lois de Rayleigh')
            plt.clim(-15,-18)
            plt.grid()
            plt.legend()
            plt.xlabel('X_L93 [m]')
            plt.ylabel('Y_L93 [m]')
        
        
        
        # plt.axes('equal') 
      
            plt.show()
        
    return d_sigma

def par_zone_classif_glissante_BS(zone_,d,nbping,sampling,d_BS_ref):
    '''
    

    Parameters
    ----------
    zone_ : Str,
        Zone à étudier (cf. returns)
    d : Dictionnaire,
        Donnée chargée par la fonction load_data
    nbping : Int,
        Cf. fonction ci-dessus, ou main
    sampling : Int,
        Cf. fonction ci-dessus, ou main
    d_BS_ref : Dictionnaire
        Cf. fonction ci-dessus, ou main

    Returns
    -------
    Affiche un subplot des valeurs prises par sigma le long de chaque ligne, 
    ces valeurs sont calculés sur une fenêtre de tailel nbping
    elles sont échantillonnées par le paramètre sampling
    L'autre figure du subplot est générée par une autre fonction (cf. main.)

    '''

    
    
    list_color_zone = ['tab:blue','tab:orange','tab:green','tab:red','tab:purple']
    
    
       #zone1bis: 
    # zone1 = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
        # zone 1:
    # zone1 = Polygon([[148111, 6831022], [148059, 6831120], [148137, 6831177], [148200, 6831088]])
    zone2 = Polygon([[148097, 6830111], [148039, 6830173], [148119, 6830245], [148173, 6830177]])
    zone3 = Polygon([[147665, 6829667], [147586, 6829740], [147663, 6829810], [147727, 6829746]])
    zone4 = Polygon([[147197, 6829228], [147130, 6829306], [147200, 6829366], [147258, 6829301]])
    zone5 = Polygon([[146527, 6830611], [146510, 6830712], [146694, 6830745], [146723, 6830635]])
    if compute_on_zone1bis :
        zone1 = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
    else :
        zone1 = Polygon([[148111, 6831022], [148059, 6831120], [148137, 6831177], [148200, 6831088]])
        # zone1bis = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
        
        
    zone = zone_
            
    line = d_BS_ref[zone]['lines'][0]
    
    
   
    plt.subplot(122)
    
    plt.axis('equal')
    
    plt.title('$\hat{\sigma}$ - Calculés sur '+str(nbping) + ' pings via fenêtre glissante')
    
    if line == 'L0008':
        zone = 'Zone 1'
        if BS_ref_with_zone :
            label_zone = '\nPings séléctionnés pour calculer $\hat{\sigma}_'+zone[-1]+'$ =' + str(d_BS_ref[zone]['sigma']) + ' dB'
        else : 
            label_zone = ' '
        x,y = zone1.exterior.xy
        plt.plot(x, y, color=list_color_zone[0],
             linestyle = '--', zorder=2, label = zone + ' - ' + d_BS_ref[zone]['sedi'] + label_zone)
    
    if line == 'L0018':
        zone = 'Zone 4'
        if BS_ref_with_zone :
            label_zone = '\nPings séléctionnés pour calculer $\hat{\sigma}_'+zone[-1]+'$ =' + str(d_BS_ref[zone]['sigma']) + ' dB'
        else : 
            label_zone = ' '
        x,y = zone4.exterior.xy
        plt.plot(x, y, color=list_color_zone[3],
             linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
    
    if line == 'L0019':
        x,y = zone2.exterior.xy
        x_,y_ = zone3.exterior.xy
        if zone == 'Zone 2':
            x,y = zone2.exterior.xy
            x_,y_ = zone3.exterior.xy
            zone = 'Zone 2'
            if BS_ref_with_zone :
                label_zone = '\nPings séléctionnés pour calculer $\hat{\sigma}_'+zone[-1]+'$ =' + str(d_BS_ref[zone]['sigma']) + ' dB'
            else : 
                label_zone = ' '
            plt.plot(x, y, list_color_zone[1],
                 linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
        else :
            zone = 'Zone 3'
            if BS_ref_with_zone :
                label_zone = '\nPings séléctionnés pour calculer $\hat{\sigma}_'+zone[-1]+'$ =' + str(d_BS_ref[zone]['sigma']) + ' dB'
            else : 
                label_zone = ' '
            
            plt.plot(x_, y_, color=list_color_zone[2],
                 linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
        
    if line == 'L0024':
        
        zone = 'Zone 5'
        if BS_ref_with_zone :
            label_zone = '\nPings séléctionnés pour calculer $\hat{\sigma}_'+zone[-1]+'$ =' + str(d_BS_ref[zone]['sigma']) + ' dB'
        else : 
            label_zone = ' '
        x,y = zone5.exterior.xy
        plt.plot(x, y, color=list_color_zone[4],
             linestyle = '--', zorder=2,label = zone + ' - ' + d_BS_ref[zone]['sedi']+ label_zone)
    
    # affichage relatifs aux prélèvements :

    if line in d_BS_ref[zone]['lines']:
        added = False
        added_ = False
        for prelev in d_prelev[zone]:
            if not added :
                labell = 'Prélèvements'
            if added :
                labell = None
            added = True
            
            xp = d_prelev[zone][prelev][0]
            yp = d_prelev[zone][prelev][1]
            
            plt.scatter(xp,yp,marker = '+',s=60,color = d_BS_ref[zone]['color'],label = labell)
            
            if BS_ref_with_circle :
                theta = np.linspace(0, 2*np.pi, 100)
                r = empreinte
                x1 = r*np.cos(theta) + xp
                x2 = r*np.sin(theta) + yp
                
                if not added_:
                    label = 'Pings séléctionnés pour calculer $\hat{\sigma}_'+zone[-1]+'$ =' + str(d_BS_ref[zone]['sigma']) + ' dB'
                else :
                    label = None
                plt.plot(x1, x2,color = d_BS_ref[zone]['color'], linewidth = 0.8, linestyle = ':', label = label)
                added_ = True
                
    # Affichage des valeurs de sigma calculées sur moyenne glissante      
    sigma_values = d_sigma[line]['sigma'].values
    z = sigma_values
    X = d_sigma[line]['X'].values
    Y = d_sigma[line]['Y'].values
    
    if freq == '38 kHz':
        sc = plt.scatter(X, Y, c=z, vmin=-14,vmax = -18, s=35, cmap='viridis')
   
    elif freq == '200 kHz':
        sc = plt.scatter(X, Y, c=z, vmin=-17,vmax = -23, s=35, cmap='viridis')
    cbar = plt.colorbar(sc)
    cbar.set_label('$\hat{\sigma}$ [dB] - Estimateur du maximum de vraissemblance sur la lois de Rayleigh')
    if freq == '38 kHz':
        plt.clim(-14,-18)
    elif freq == '200 kHz':
        plt.clim(-17,-23)
    plt.grid()
    plt.legend()
    plt.xlabel('X_L93 [m]')
    plt.ylabel('Y_L93 [m]')
    
    
    
    # plt.axes('equal') 

        
    return None

def addZone(d,line):

    
    """ Cette fonction permet d'identifier la zone des pings"""
    
    data = d[line]['data']
    data['Zone'] = np.zeros((data.shape[0]))
    #old zones
    # zone1 = Polygon([[147932, 6830864], [147826, 6830989], [148120, 6831205], [148214, 6831077]])
    # zone2 = Polygon([[148026, 6830005], [147945, 6830093], [148170, 6830312], [148255, 6830225]])
    # zone3 = Polygon([[147591, 6829582], [147512, 6829661], [147741, 6829883], [147819, 6829805]])
    # zone4 = Polygon([[147099, 6829122], [147027, 6829206], [147227, 6829382], [147299, 6829303]])
    # zone5 = Polygon([[146456, 6830591], [146434, 6830713], [146726, 6830760], [146754, 6830635]])

    # new zones
    # zone1 = Polygon([[148111, 6831022], [148059, 6831120], [148137, 6831177], [148200, 6831088]])
    zone2 = Polygon([[148097, 6830111], [148039, 6830173], [148119, 6830245], [148173, 6830177]])
    zone3 = Polygon([[147665, 6829667], [147586, 6829740], [147663, 6829810], [147727, 6829746]])
    zone4 = Polygon([[147197, 6829228], [147130, 6829306], [147200, 6829366], [147258, 6829301]])
    zone5 = Polygon([[146527, 6830611], [146510, 6830712], [146694, 6830745], [146723, 6830635]])
    
    if compute_on_zone1bis :
        zone1 = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
    else :
        zone1 = Polygon([[148111, 6831022], [148059, 6831120], [148137, 6831177], [148200, 6831088]])
    for index, row in data.iterrows():
        ping = Point(row['X_Beam'], row['Y_Beam'])
        if zone1.contains(ping):
            row['Zone'] = 1
        # elif zone1bis.contains(ping):
        #     row['Zone'] = 6
        elif zone2.contains(ping):
            row['Zone'] = 2
        elif zone3.contains(ping):
            row['Zone'] = 3
        elif zone4.contains(ping):
            row['Zone'] = 4
        elif zone5.contains(ping):
            row['Zone'] = 5
        data.at[index] = row

    d[line]['data'] = data
    return d


def export_sigma(d_sigma,path,freq,only_zone):
    '''
    

    Parameters
    ----------
    d_sigma : Dictionnaire
        Valeurs de sigma calculées via fenêtre glissante le long de chaque ligne
    path : Str,
        Répertoire où stocker les données
    freq : Str,
        Fréquence d'étude'
    only_zone : Booléen,
        Pour en garder les valeurs de sigma qui ne correspondent qu'à l'empreinte
        géographique de chaque zone de référence

    Returns
    -------
    Sauvegarde les fichiers au format txt.

    '''
    
    for line in d_sigma:
        
        fic = line + '_' + 'zone_X_Y_sigma_' + freq
        fic_only_zone = line + 'zone_only_' + 'zone_X_Y_sigma_' + freq
        
        df = d_sigma[line]
        
        df_mask = df['Zone']!= 0
        df_filtered = df[df_mask]
        
        if not only_zone :
            np.savetxt(path+fic, df.values, delimiter = ' ',fmt = '%.5f')
        if only_zone :
            
            np.savetxt(path+fic_only_zone, df_filtered.values, delimiter = ' ',fmt = '%.3f')
    
    return None

if __name__=='__main__':
    
    plt.close('all') # Fermer toutes les figures encore ouvertes
    
    
    # fréquence analysé :
    ''' Choix de la fréquence à analyser, chaîne de caractère '''
    
    freq = '200 kHz'
    
    # ----- CHEMINS VERS LES REPERTOIRES -----
    
    dir_path = './fic_h5_nadir_AllData_38/' # repertoire d'entree contenant les fichiers h5
    
    files38_h5 = glob.glob(dir_path+'*_38kHz_data2.h5') # Ensemble des fichiers h5 à 38kHz à traiter (chemins)
    files200_h5 = glob.glob(dir_path+'*_200kHz_data.h5') # Ensemble des fichiers h5 à 200kHz à traiter (chemins)
    
    if freq == '38 kHz':
        dir_path = './fic_h5_nadir_AllData_38/'
        files_all_data_ref = glob.glob(dir_path+'*_AllData.h5')
    if freq == '200 kHz':
        dir_path = './fic_h5_nadir_AllData_200/'
        files_all_data_ref = glob.glob(dir_path+'*_AllData.h5')
        
    # Chemins vers les MNT
    d_mnt = {1:'./MNT/MNT_Zone1_07102020_L93.tif',2:'./MNT/MNT_Zone2_07102020_L93.tif',3:'./MNT/MNT_Zone2_07102020_L93.tif',4:'./MNT/MNT_Zone2_07102020_L93.tif',5:'./MNT/MNT_Zone3_07102020_L93.tif'}
        
    # ----- CHARGEMENT DE LA BASE DE DONNEES -----
    
    
    d = load_data(files_all_data_ref) 
    
    
    #----- VARIABLES ------
    bras_levier = [1.2565,1.21,1.881] # Bras de levier x,y,z
    patch_test  = [0.379,-0.293,1.17] # Patch test x,y,z
    
 
    
    #----- Choix des lignes à traiter ------
    ''' Dans le paramètres 'lines', qui est une liste,
        sous forme de chaînes de caractère 
        e.g : lines = ['L0019','L0006'] '''
    # paramètres ligne (ligne à traiter) ; lines, (lignes à traiter) #########
    # on traite toutes les lignes de d
    lines = []
    for l in d:
        if l not in lines:
            lines.append(l)
    
     
    #----- Calcul du BS ------
    ''' Se référer à al fonction compute_BS pour la méthode de calcul (nadir ou pas)'''
    
    for line in lines:
        if freq == '38 kHz' :
            d_ = compute_BS(d,line) # ajout de la valeur de BS calcule dans le dictionnaire
            d = d_
            filepath = dir_path + line + '_ref.txt' # Répertoire des fichiers Kongsberg, 
                                                    # il y en a un par ligne, au format .txt
            L_Kongsberg = pandas.read_csv(filepath,sep=' ') 
            Kongsberg = L_Kongsberg[['DateTime','BS_38']] 
            depth_kongsberg = L_Kongsberg['Depth_38']
            # plotCompareBS(d,line,Kongsberg,'BS Comparison '+ line) # Pour comparer le BS calculé
                                                                     # et le BS Kongsberg
            # plt.show() 
        elif freq == '200 kHz':
            d3 = compute_BS(d,line) 
            d = d3
            filepath = dir_path + line + '_ref.txt'
            L_Kongsberg = pandas.read_csv(filepath,sep=' ') 
            Kongsberg = L_Kongsberg[['DateTime','BS_200']]
            depth_kongsberg = L_Kongsberg['Depth_200']
            # plotCompareBS(d,line,Kongsberg,'BS Comparison '+ line)
            # plt.show()
   
    
    # paramètres caractérisant chaque zone : leur nom, la couleur voulue pour 
    # afficher les figures, et leur type de sédiment (idem, pour l'affichage)
    list_zone = ['Zone 1', 'Zone 2', 'Zone 3', 'Zone 4', 'Zone 5']
    list_color_zone = ['tab:blue','tab:orange','tab:green','tab:red','tab:purple']
    list_sedi_zone = ['Vase','Sable et vase','Sable et graviers','Roches','Graviers']
    
    # Variable contenant les coordonés des prélèvements sédimentaires, par zone :
    compute_on_zone1bis = False
    d_prelev = {}
    d_prelev['Zone 1'] = {}
    d_prelev['Zone 2'] = {}
    d_prelev['Zone 3'] = {}
    d_prelev['Zone 4'] = {}
    d_prelev['Zone 5'] = {}
    
    # paramètre de recherche des ping autour de chaque prélèvement, en mètre,
    # pour l'analyse de la distribution des valeurs de BS par zone
    empreinte = 25
    
    # Permet de choisir les pings contenu dans un cercle de rayon 'empreinte',
    # centré sur chaque prélèvement (cf. dictionnaire 'd_prelev') de chaque zone
    # Ces pings seront séléctionnés pour analyser la distribution des valeurs de BS 
    # de la zone dont ils sont issus
    BS_ref_with_circle = False
    
    # Permet de choisir les pings contenu dans l'ensemble de la zone 
    # (définis par le paramètre 'zone' dans l'objet 'd['data'][line]')
    # pour étudier la distribution des valeurs de BS par zone
    BS_ref_with_zone = True
    
    # Permet de choisir manuellement les coordonnés de points
    # autour desquels on considérera que le prélèvement a été fait
    # Càd : permet de séléctionner les pings contenu dans le cercle 
    # de rayon 'empreinte' centré sur un ou plusieurs points 
    # choisis manuellement pour l'étude de la distribution des valeurs de BS par zone
    manual_choice = False
    
  
    
    for zone in d_prelev:
        # X,Y L93 dans la liste correspondant à chaque prélèvement
        if zone == 'Zone 1':
            if not manual_choice:
                # d_prelev[zone]['1'] = []
                d_prelev[zone]['2'] = [148108.86, 6831054.47]
                d_prelev[zone]['3'] = [148040.21	,6831045.27]
            else :
                d_prelev[zone]['1'] = [147995	,6831010]
                # d_prelev[zone]['2'] = [147990	,6831000]
            
        if zone == 'Zone 2':
            if not manual_choice :
                d_prelev[zone]['1'] = [148094.36	,6830147.1]
                d_prelev[zone]['2'] = [148116.08	, 6830170.2]
                d_prelev[zone]['3'] = [148094.5	, 6830180.06]
                # d_prelev[zone]['4'] = [148058.58, 6830211.43]
            else :
                d_prelev[zone]['1'] = [148118	, 6830180.06]
                
        if zone == 'Zone 3':
            if not manual_choice :
                d_prelev[zone]['1'] = [147652.23	,6829731.77]
                d_prelev[zone]['2'] = [147678.03, 6829747.9]
                d_prelev[zone]['3'] = [147661.27	,6829733.93]
            else :
                d_prelev[zone]['1'] = [147652.23	,6829731.77]
                d_prelev[zone]['2'] = [147678.03, 6829747.9]
                
        if zone == 'Zone 4':
            if not manual_choice :
                d_prelev[zone]['1'] = [147184.42,	6829270.46]
                d_prelev[zone]['2'] = [147185.86, 6829259.6]
                d_prelev[zone]['3'] = [147191.29,	6829303.08]
            else :
                d_prelev[zone]['1'] = [147203.42,	6829300.46]
        if zone == 'Zone 5':
            if not manual_choice :
                d_prelev[zone]['1'] = [146601.01,	6830682.66]
                d_prelev[zone]['2'] = [146592.82,6830677.89]
                d_prelev[zone]['3'] = [146605.52	,6830698.62]
            else :
                d_prelev[zone]['1'] = [146592.01,	6830670.66]
   
    
    
    
    # Fonction permettant de réduire la taille initiale des zones
    # et de modifier le dictionnaire 'd' en conséquence
    if BS_ref_with_zone :
        for l_ in d:
            d = addZone(d,l_)
    
    # d_BS_ref : contient des infos sur l'étude du BS par zone de reférence : notamment sigma,
    # mais aussi la nature du sédiment
    
    print_fig = False # Permet d'afficher séparément l'histograme des valeurs de BS
                      # et les valeurs de sigma calculées par fenêtre glissante
    print_subplot = True # Permet de les afficher sur la même figure
   
    facteur_bins = 15 # Bins pour l'histograme des valeurs de BS
    d_BS_ref = classif_BS(d,freq,empreinte,BS_ref_with_circle,BS_ref_with_zone,print_fig)
    # Paramètre pour le calcul de sigma par fenêtre glissante :
        # nbping = taille de la fenêtre en nombre de ping
        # sampling = fréquence d'échantillonnage pour le calcul des valeurs de sigma
        # (sampling = 10 veut dire qu'on calculera une valeur de sigma un ping sur 10 le long de la ligne)
    nbping,sampling = 100,1
    
    # Fonction permettant d'afficher les valeurs de sigma calculés par fenêtre glissante
    # et de remplir leur valeur par ligne et par zone dans le dictionnaire 'd_sigma'
    d_sigma = classif_glissante_BS(d,nbping,sampling,d_BS_ref,print_fig) 
    
    
    for zone_to_print in d_BS_ref:
        if print_subplot:
            plt.figure()
            plt.suptitle('Etude de la répartition des indices de rétrodiffusion - ' + zone_to_print + ' - ' + d_BS_ref[zone_to_print]['lines'][0] + ' - ' + freq)
            par_zone_classif_BS(facteur_bins,zone_to_print,d,freq,empreinte,BS_ref_with_circle,BS_ref_with_zone)
            par_zone_classif_glissante_BS(zone_to_print,d,nbping,sampling,d_BS_ref)
            plt.show()
    
    
    # export de données, valeurs de sigma calculées via fenêtre glissante, par ligne :
    
    # export :
    only_zone = False
    if not only_zone :
        path = './fic_sigma_nadir/' # répertoire d'enregistrement des données sigma
                                    # on ne garde que les valeurs correspondant aux zones de référence
    if only_zone:
        path = './fic_sigma_zone_only/' # répertoire d'enregistrement des données sigma
                                        # on garde les valeurs de sigma sur toutes les lignes de levé
        
    export_sigma(d_sigma,path,freq,only_zone)
    
    
    

    
    
    