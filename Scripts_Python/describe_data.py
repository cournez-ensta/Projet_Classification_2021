#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Auteur : Aelaig COURNEZ - Flora GUES - Yann LAMBRECHTS - Romain SAFRAN


# Librairies importee
import numpy as np
import pandas
import matplotlib.pyplot as plt
import glob
import scipy.signal as scs
from sklearn.cluster import KMeans
from shapely.geometry import Point, Polygon
# Scripts
import analyse_data as an
import script_romain as scr


#--------------------------------------------------------------------------------#
#           DESCRIPTION DES DONNEES EA400 POUR LA CLASSIFICATION                 #
#                                                                                #
#   Ce code est compose d'un certain nombre de fonctions permettant de           #
#   traiter les donnees issues des acquisitions EA400 et d'analyser les          #
#   caracteristiques acoustiques des echos temporels au nadir afin de proposer   #
#   une classification des differentes natures de fond.                          #
#   Pour utiliser ce script, il faut avoir genere des fichiers h5 comprenant     #
#   l'ensemble des donnees acoustiques, ainsi que les traitements (position      #
#   des sondes + angle d'incidence + valeur de BS).                              #
#--------------------------------------------------------------------------------#


#-------- FONCTION PERMETTANT DE CARACTERISER LES ECHOS ACOUSTIQUES AU NADIR --------


def changeZone(d,line):
    """
    Cette fonction permet de modifier la valeur de l'attribut 'Zone' lorsque l'on reduit l'emprise des zones d'etude.

    Parametres
    ----------
    d : TYPE
        DESCRIPTION.
    line : TYPE
        DESCRIPTION.

    Sortie
    -------
    d : TYPE
        DESCRIPTION.

    """
    data = d[line]['data']
    data['Zone'] = np.zeros((data.shape[0]))

    # new zones
    # zone1 = Polygon([[148111, 6831022], [148059, 6831120], [148137, 6831177], [148200, 6831088]])
    zone2 = Polygon([[148097, 6830111], [148039, 6830173], [148119, 6830245], [148173, 6830177]])
    zone3 = Polygon([[147665, 6829667], [147586, 6829740], [147663, 6829810], [147727, 6829746]])
    zone4 = Polygon([[147197, 6829228], [147130, 6829306], [147200, 6829366], [147258, 6829301]])
    zone5 = Polygon([[146527, 6830611], [146510, 6830712], [146694, 6830745], [146723, 6830635]])
    
    zone1 = Polygon([[147909, 6831018], [147970, 6831058], [148045, 6830968], [147981, 6830911]])
    
    for index, row in data.iterrows():
        ping = Point(row['X_Beam'], row['Y_Beam'])
        if zone1.contains(ping):
            row['Zone'] = 1
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



def compute_Pref(i,depth,time,nbPing,nbSmp,dref,avrPing):
    """
    Cette fonction permet de transformer les donnees mesurees a une profondeur de reference
    afin de retirer l'effet de la profondeur dans l'analyse de l'echo.
    Cette transformation se compose d'un ajustement energetique et d'un ajustement temporel.

    Parametres
    ----------
    i : matrix
        puissance enregistree par le sondeur  en watt pour chaque ping sur une ligne de leve
    depth : array
        profondeur de detection associee a chaque ping
    time : array
        vecteur temps des pings
    nbPing : int
        nombre de ping total
    nbSmp : int
        nombre d'echantillons par ping
    dref : int
        profondeur de reference a laquelle on souhaite se ramener
    avrPing : int
        nombre de pings a prendre en compte lors de la moyenne glissante
        
    Sortie
    -------
    i_filtred : matrix
        puissance corrigee par une transformation a une profondeur de reference

    """
    for p in range(0,nbPing): # on parcourt les pings d'une ligne de leve
        # ajustement temporel
        t_ref = dref * time[1] / depth[p]
        time_ref = np.arange(0, nbSmp) * t_ref
        i[:,p] = np.interp(time,time_ref,i[:,p])
        # ajustement de la puissance
        i[:,p] =i[:,p]*(depth[p]/dref)**3 
    # Moyenne glissante 
    b = np.arange(1,avrPing)/avrPing
    a = 1
    i_filtred = scs.lfilter(b,a,i,axis=1) # filtrage
    return(i_filtred)



def find_nearest(array, value):
    """
    Cette fonction permet d'acceder a l'indice associe a une valeur de temps donnee

    Parametres
    ----------
    array : array
        vecteur temps
    value : float
        valeur de temps

    Sortie
    -------
    idx : int
        indice du temps le plus proche de la valeur en entree
    """
    idx = (np.abs(array - value)).argmin()
    return idx



def compute_E1_E2_E3(i_filtred,c,PulseLenght,time,nbPing,dref):
    """
    Cette fonction permet de calculer les descripteurs energetiques E1, E2 et E3.

    Parametres
    ----------
    i_filtred : matrix
        puissance corrigee a une profondeur de reference en watt
    c : float
        celerite de l'onde
    PulseLenght : float
        duree d'impulsion
    time : array
        vecteur temps
    nbPing : int
        nombre de ping sur la ligne
    dref : int
        profondeur de reference

    Sorties
    -------
    E1 : array
        valeurs de E1 pour chaque ping        
    E2 : array
        valeurs de E2 pour chaque ping
    E3 : array
        valeurs de E3 pour chaque ping
    """
    # initialisation des listes
    E1,E2,E3 = [],[],[]
    for p in range(0,nbPing):  # on parcourt les pings      
      #temps du 1er echo
      t1 =  dref*2/c

      #temps 1er echo + PulseLenght
      t2 = t1+PulseLenght
      t2_idc = find_nearest(time,t2)
      t2_stop = 2*t1*0.95
      t2_stop_idc = find_nearest(time,t2_stop)
      
      #temps du 2em echo
      t3 = t1[0]*2
      
      t3_idc = find_nearest(time,t3)
      t3_stop = 3*t1*0.95 #+Snd_Surf*2/data[line]['param']['SoundVelocity'].values
      t3_stop_idc = find_nearest(time,t3_stop)
      #tps du 3eme echo 
      t4 = t1[0]*3
      t4_idc = find_nearest(time,t4)
      t4_stop = 4*t1*0.95 #+Snd_Surf*2/data[line]['param']['SoundVelocity'].values
      t4_stop_idc = find_nearest(time,t4_stop)
      #E1  
      x = time
      E1_int = 0
      E2_int = 0
      E3_int = 0
      y = i_filtred[:,p]
    
      for j in range(t2_idc,t2_stop_idc):
          E1_int = E1_int + y[j]*(x[j+1]-x[j])
                      
      for j in range(t3_idc,t3_stop_idc):
          E2_int = E2_int + y[j]*(x[j+1]-x[j])
      
      for j in range(t4_idc,t4_stop_idc):
          E3_int = E3_int + y[j]*(x[j+1]-x[j])
          
      E1.append(E1_int)
      E2.append(E2_int)
      E3.append(E3_int)
    
    return(E1,E2,E3)



def compute_pente(i_filtred,c,PulseLenght,time,nbPing,dref):
    """
    Cette fonction permet de calculer le descripteur mprphologique appele 'Pente'
    et correspondant a la pente du premier echo de chaque ping.

    Parametres
    ----------
    i_filtred : matrix
        puissance en watt corrigee a une profondeur de reference
    c : float
        celerite de l'onde
    PulseLenght : float
        duree d'impulsion
    time : array
        vecteur temps des echantillons
    nbPing : int
        nombre de pings sur la ligne
    dref : int
        profondeur de reference choisie

    Sortie
    -------
    P : array
        valeurs de la pente du premier echo pour chaque ping

    """
    P =[] # initialisation
    for p in range(0, nbPing):
        tmax = dref * 2 / c
        ta = tmax - 3*PulseLenght # debut intervalle de temps
        tb = tmax + PulseLenght # fin intervalle de temps
        tai = find_nearest(time, ta)
        tbi = find_nearest(time, tb)
        power = 10*np.log10(i_filtred[tai:tbi,p])

        pw_min , pw_max = np.min(power) ,np.max(power) # difference en puissance
        # calcul de la pente
        pente = (pw_max-pw_min)/(tbi-tai)
        P.append(pente)
    return P



def computeDescriptors(d,lines,dref,n_moy,Freq200,NewZone,ProfRef):
    """
    Cette fonction permet d'executer le calcul des descripteurs E1, E2, E3 et de la Pente

    Parametres
    ----------
    d : dictionary
        base de donnees
    lines : list of string
        liste des lignes de leve a traiter
    dref : int
        profondeur de reference choisie
    n_moy : int
        nombre de pings a prendre en compte pour la moyenne glissante
    Freq200 : boolean
        si Freq200=True alors intervalle d'echantillonnage doit etre multiplie par 10 car nous avons reduit les donnees et considere seulement 1/10 donnee
    NewZone : boolean
        si NewZone=True alors on corrige la valeur de l'attribut 'Zone' afin de prendre en compte les zones reduites
    ProfRef : boolean
        si ProfRef=True alors on realise la transformation a une profondeur de reference

    Sortie
    -------
    d : dictionary
        base de donnees completee avec les donnees de E1,E2,E3 et Pente

    """

    for line in lines :
        if NewZone :
            d = changeZone(d, line)

        # données
        data = d[line]['data']
        Power = data['Power']
        Depth = data['Depth'].values
        # paramètres
        Celerite = d[line]['param']['SoundVelocity'].values
        PulseLenght = d[line]['param']['PulseLength'].values
        SampleInterval = d[line]['param']['SampleInterval'].values
        if Freq200:
            SampleInterval = d[line]['param']['SampleInterval'].values*10 # échantillonnage des données 1/10

        exc = False # cas L0024

        # gérer l'exception de la ligne 24
        power = np.array([np.array(li) for li in Power]).T
        if line=='L0024' or len(power.shape)==1:
            Power = Power[1:]
            Depth = Depth[1:]
            exc = True

        Power = np.array([np.array(li[:]) for li in Power[:]]).T
        nbSmp , nbPing = Power.shape[0] , Power.shape[1]

        time = np.arange(0, int(nbSmp), 1) * SampleInterval

        # conversion de dB en W
        i = 10 ** (Power / 10)
        if ProfRef:
            # calcul profondeur de reference
            i_filtred = scr.compute_Pref(i,Depth,time,nbPing,nbSmp,dref,n_moy)
        else :
            i_filtred = i
        # calcul de E1 , E2 , E3
        E1, E2, E3 = scr.compute_E1_E2_E3(i_filtred,Celerite,PulseLenght,time,nbPing,dref)
        # calcul de la pente
        P = scr.compute_pente(i_filtred, Celerite, PulseLenght, time, nbPing, dref)

        i_filtred = 10 * np.log10(i_filtred)
        i_filtred = [list(i_filtred[:, i]) for i in range(nbPing)]

        if exc:
            i_filtred.insert(0, [0] * nbSmp)
            Power = [list(Power[:, i]) for i in range(nbPing)]
            Power.insert(0, [0] * nbSmp)
            data['Power'] = Power
            E1.insert(0,0)
            E2.insert(0,0)
            E3.insert(0,0)
            P.insert(0, 0)

        data['Power_ProfRef'] = i_filtred
        data['E1'] = E1
        data['E2'] = E2
        data['E3'] = E3
        data['Ping_pente'] = P

        d[line]['data'] = data

    return d


#-------------- CREATION DES DICTIONNAIRES ZONES --------------

def getDictZone(d,lines):
    """
    Cette fonction permet de reorganiser les donnees non plus en fonction des lignes de leve d[line] 
    mais desormais selon les zones d'etude d[zone].

    Parametres
    ----------
    d : dictionary
        base de donnees organisee selon les lignes de leve
    lines : list of string
        lignes de leves a enregistrer

    Sortie
    -------
    d_zone : dictionary
        base de donnees organisee selon les zones d'etudes

    """
    d_zone1 = pandas.DataFrame()
    d_zone2 = pandas.DataFrame()
    d_zone3 = pandas.DataFrame()
    d_zone4 = pandas.DataFrame()
    d_zone5 = pandas.DataFrame()
    
    for line in lines:
        data = d[line]['data']
        d_zone1 = d_zone1.append(data.loc[data['Zone']==1],ignore_index=True)
        d_zone2 = d_zone2.append(data.loc[data['Zone']==2],ignore_index=True)
        d_zone3 = d_zone3.append(data.loc[data['Zone']==3],ignore_index=True)
        d_zone4 = d_zone4.append(data.loc[data['Zone']==4],ignore_index=True)
        d_zone5 = d_zone5.append(data.loc[data['Zone']==5],ignore_index=True)
    d_zone = [d_zone1,d_zone2,d_zone3,d_zone4,d_zone5]
    return d_zone



#-------------- FONCTIONS D'AFFICHAGE --------------


def plotPingMean(d_zone,xmin,xmax,n_Ping,colors,title):
    """
    Cette fonction permet de visualiser les premiers echos moyens caracteristiques de chaque zone d'etude'

    Parametres
    ----------
    d_zone : dictionary
        base de donnees
    xmin : int
        echantillon minimal pour l'affichage
    xmax : int
        echantillon maximal pour l'affichage
    n_Ping : int
        nombre de ping a prendre en compte
    colors : list of string
        code couleur pour les zones d'etude
    title : string
        titre de la figure affichee

    """
    plt.figure(figsize=(5,18))
    plt.suptitle(title)
    plt.title('Moyenne sur 300pings avec correction à une prof de réf')
    for z in range(5):
        power = d_zone[z].loc[:,'Power_ProfRef']
        power = np.array([np.array(li) for li in power]).T
        # calcul du ping moyen
        ping_mean = np.mean(power[:,:n_Ping],axis=1)
        # affichage du ping moyen
        plt.subplot(5,1,z+1)
        plt.plot(ping_mean[xmin:xmax],label='Zone '+str(z+1),c=colors[z])
        plt.legend()
    plt.xlabel('Echantillons')
    plt.ylabel('Puissance [db]')
    return None



def plotAllEchogram(d_zone,value,n_Ping):
    """
    Cette fonction permet d'afficher les echogrammes des donnees considerees sur chaque zone
    Cela permet notamment de visualiser l'effet de la correction a une profondeur de reference

    Parametres
    ----------
    d_zone : dictionary
        base de donnees
    value : string
        attribut a visualiser, soit 'Power' (sans correction) soit 'Power_ProfRef' (avec correction)
    n_Ping : int
        Dnombre de pings a prendre en compte

    """
    plt.figure()
    for z in range(5):
        power = d_zone[z].loc[:,value]
        power = np.array([np.array(li) for li in power]).T
        plt.subplot(1,5,z+1)
        plt.imshow(power[:,:n_Ping])
        plt.title('Zone '+str(z+1))
    return None



def plotHistDescripteur(list_des,title,xlabel,colors,hist_min,hist_max):
    """
    Cette fonction permet d'afficher les histogrammes associes a la distribution des valeurs de descripteurs pour chaque zone d'etude.

    Parametres
    ----------
    list_des : list of list
        listes des valeurs des descripteurs pour chaque zone d'etude (1 liste par zone)
    title : string
        titre de la figure a afficher
    xlabel : string
        texte de la legende de l'abscisse
    colors : list of string
        code couleur pour chaque zone
    hist_min : float
        valeur minimale de l'intervalle de valeurs a afficher
    hist_max : TYPE
        valeur maximale de l'intervalle de valeurs a afficher

    """
    plt.figure(figsize=(8,18))
    plt.suptitle(title)
    for z in range(5):
        plt.subplot(5,1,z+1)
        # affichage des histogrammes
        plt.hist(list_des[z],color=colors[z],bins=50,histtype='stepfilled', alpha=0.3,label='Zone '+str(z+1)) # couleurs au fond des histogrammes
        plt.hist(list_des[z],color=colors[z],bins=50,histtype='step') # couleurs de contour des histogrammes
        plt.xlim((hist_min,hist_max))
        plt.legend()
    plt.xlabel(xlabel)
    return None



def plotE1E2(d_zone,n_ping,title,E1_lim,E2_lim):
    """
    Cette fonction permet d'afficher les donnees E1, E2 selon le plan E1 en fonction de E2.

    Parametres
    ----------
    d_zone : dictionary
        base de donnees
    n_ping : int
        nombre de pings a prendre en compte
    title : string
        titre de la figure a afficher
    E1_lim : list of float
        intervalle des valeurs E1 a afficher
    E2_lim : list of float
        intervalle des valeurs E2 a afficher

    """
    plt.figure()
    plt.title(title)
    for z in range (5):
        E1 = d_zone[z].loc[:,'E1'][:n_ping]
        E2 = d_zone[z].loc[:,'E2'][:n_ping]
        # affichage du nuage de point
        plt.scatter(E2,E1,marker='.',label='Zone '+str(z+1))
    plt.ylim(E1_lim)
    plt.xlim(E2_lim)
    plt.xlabel('Indice de dureté - E2')
    plt.ylabel('Indice de rugosité - E1')
    plt.legend()
    return None



#-------------- CLASSIFICATION PAR K-MOYENNES --------------

def computeKMeans(d_zone,k,descripteurs,n_ping):
    """
    Cette fonction permet de tester les performances des descripteurs en appliquant une classification par k-moyennes sur l'ensemble des donnees

    Parametres
    ----------
    d_zone : dictionary
        base de donnees
    k : int
        nombre de classes a chercher
    descripteurs : list of string
        liste des descripteurs a prendre en compte
    n_ping : int
        nombre de ping a prendre en compte pour chaque zone

    Sorties
    -------
    d_zone_new : dictionary
        dictionnaire comprenant l'attribut 'Class' associe a chaque ping
    d_all : dictionary
        dictionnaire rassemblant l'ensemble des donnees utiles - pratique pour faire un export des donnees en csv.

    """
    d_all = pandas.DataFrame()
    # construction de la base de donnees a fournir en entree de l'algorithme de k-moyennes
    for d_zi in d_zone:
        d_zi_sub = d_zi[['X_Beam', 'Y_Beam','Zone','BS_calc','E1','E2','E3','Ping_pente']][:n_ping]
        d_all = d_all.append(d_zi_sub)
    d_desc = d_all[descripteurs]
    d_desc = (d_desc-d_desc.mean())/d_desc.std()
    X = d_desc.values
    
    # classification par k-moyennes
    kmeans = KMeans(n_clusters=k, random_state=0).fit(X)
    d_all['Class'] = kmeans.labels_
    
    # completer la base de donnee finale d_all
    d_zone1 = d_all.loc[d_all['Zone']==1]
    d_zone2 = d_all.loc[d_all['Zone']==2]
    d_zone3 = d_all.loc[d_all['Zone']==3]
    d_zone4 = d_all.loc[d_all['Zone']==4]
    d_zone5 = d_all.loc[d_all['Zone']==5]
    d_zone_new = [d_zone1,d_zone2,d_zone3,d_zone4,d_zone5]
    return d_zone_new , d_all



def plotClassHist(d_zone,k,n_ping):
    """
    Cette fonction permet d'afficher la repartition des classes identifiees par k-moyennes sur chaque zone d'etude

    Parametres
    ----------
    d_zone : dictionary
        base de donnees
    k : int
        nombre de classes identifiees
    n_ping : int
        nombre de pings a prendre en compte

    """
    # code couleur pour l'affichage
    colors = ['darkturquoise','darkorange','yellowgreen','hotpink','blueviolet']
    colors = [ 'lightseagreen','gold','indianred','yellowgreen','orchid']
    label = ['Zone '+str(i) for i in range(1,6)]
    plt.figure(figsize=(8,5))
    # variable cumul permettant l'affichage des proportions cumulees
    cumul=np.zeros(5)
    for c in range(k):
        count =[]
        for z in range(5):
            data = d_zone[z]
            count.append(len(data.loc[data['Class']==c]))
        count = np.array(count)/n_ping*100
        # affichage du diagramme
        plt.barh(label,count,left=cumul, label='Classe '+chr(65+c),color=colors[c],alpha=0.8)
        cumul = cumul+np.array(count)
    plt.xlabel('Pourcentage (%)')
    plt.legend(bbox_to_anchor=(0,1.02,1,0.2), loc="lower left",mode="expand", borderaxespad=0, ncol=5)
    plt.gca().invert_yaxis()
    return None




if __name__=='__main__':
    
    plt.close('all') # Fermer toutes les figures encore ouvertes
    
    #----- CHEMINS VERS LES REPERTOIRES -----

    dir_path_38 = './fic_h5/'  # repertoire d'entree contenant les fichiers h5
    files38_h5 = glob.glob(dir_path_38 + '*.h5')  # Ensemble des fichiers h5 à 38kHz à traiter (chemins)

    dir_path_200 = './fic_h5_nadir_200kHz_AllData/' # repertoire d'entree contenant les fichiers h5
    files200_h5 = glob.glob(dir_path_200+'*.h5') # Ensemble des fichiers h5 à 38kHz à traiter (chemins)
           
    # #----- CHARGEMENT DE LA BASE DE DONNEES -----
    
    d_38 = an.load_data(files38_h5) # Donnees 38kHz
    # d_200 = an.load_data(files200_h5)  # Donnees 200kHz
    print('Chargement acheve')

    # #----- VARIABLES -----
    
    lines = ['L0008','L0018','L0019','L0024']
    colors = ['tab:blue','tab:orange','tab:green','tab:red','tab:purple']
    prof_ref = 15 # profondeur de reference
    n_moy = 5 # moyenne glissante
    x_min , x_max , n_ping = 50,300,110  # affichage des données
    k = 5
    descripteurs = ['BS_calc','E1','E2','E3','Ping_pente']
    Freq200 = False
    NewZone = True
    ProfRef = True

    #----- CALCULS DESCRIPTEURS 38kHz -----

    # computeDescriptors(d_38, lines, prof_ref, n_moy,Freq200,NewZone,ProfRef)

    # d_38_zone = getDictZone(d_38, lines)
    
    
    #----- AFFICHAGE DES DESCRIPTEURS -----
    
    # E1_lim , E2_lim ,E3_lim = (-5e-9, 2e-7) , (-5e-10,2e-8) , (-5e-12, 4e-10) #new zone
    # E1_lim, E2_lim, E3_lim = (-5e-9, 2e-6), (-5e-10, 5e-8), (-5e-11, 8e-10)

    # plotE1E2(d_38_zone,n_ping,'',E1_lim,E2_lim)
    
    # E1_38 , E2_38 ,E3_38 ,P_38 = [] ,[],[],[]
    # BS_38 = []
    # for d_zi in d_38_zone:
    #     E1_38.append(d_zi.loc[:, 'E1'][:n_ping])
    #     E2_38.append(d_zi.loc[:, 'E2'][:n_ping])
    #     E3_38.append(d_zi.loc[:, 'E3'][:n_ping])
    #     P_38.append(d_zi.loc[:, 'Ping_pente'][:n_ping])
    #     BS_38.append(np.array(10**(d_zi.loc[:, 'BS_calc'][:n_ping]/10)))
    
    # hist_min,hist_max = E1_lim
    # plotHistDescripteur(E1_38, 'Histogrammes E1 - 38kHz','E1', colors, hist_min, hist_max)

    # plotPingMean(d_38_zone, 40, 140, n_ping, colors, 'Echo moyen - 38kHz')
    
    # hist_min, hist_max = (2,6)
    # plotHistDescripteur(P_38, 'Histogrammes Pente - 38kHz\n pente en dB/sec','Pente', colors, hist_min, hist_max)
    
    #----- CLASSIFICATION PAR K-MOYENNES -----
    
    # d_38_zone_class , d_all = computeKMeans(d_38_zone,k,descripteurs,n_ping)

    # plotClassHist(d_38_zone_class,k,n_ping)

    plt.show()
