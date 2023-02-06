import numpy as np
from astropy.io import fits
import inspect
import time

def read_fits_table2dict(f,hdu):
    '''
    reads arbitrary fits table and creates dictionary with information
    using the first column as identifier
    '''
    
    hdulist = fits.open(f)
    tbdata = hdulist[hdu]._hdu
    tbcols = hdulist[hdu].columns
    hdulist.close()
    info = {}
    for col in tbcols.names:
        info[col] = tbdata[col]

    # find the column containing the IDs
    try:
        if 'ID' in list(info[tbcols.names[0]]):
            ids = info[tbcols.names[0]]
        else:
            try: 
                ids = info['ID']
            except:
                here_ids = [i for i in tbcols.names if 'ID' in i]
                ids = info[here_ids[0]]    
    except:
        ids = info[tbcols.names[0]]

    info_ids = {}
    for i in range(len(ids)):
        id_params = {}
        for c in info.keys():
            id_params[c] = info[c][i]
        info_ids[str(ids[i])] = id_params

    return info,info_ids


def write_table_from_dict_in_dict(d,f):
    '''
    Write a fits table using a dictionary with dictionaries using the
    keys as first column and the keys of the inner dictionaries as other
    columns. 
    d = dictionary
    f = name and directory of output file
    '''

    all_cols_content = reshape_dict_in_dict(d,'ID')

    # test datatype of contents
    data_types = {}
    for c in all_cols_content:
        values = all_cols_content[c]
        if type(values[0]) in [int,np.int64,np.int16,np.uint8]:
            data_types[c] = 'K'
        elif type(values[0]) in [np.float16,np.float32,np.float64,np.float]:
            data_types[c] = 'D'
        elif type(values[0]) in [str,np.str_]:
            data_types[c] = '100A'
        elif type(values[0]) in [np.bool, np.bool_]:
            data_types[c] = 'L'
        else:
            print("Didn't understand datatype: ",type(values[0]),' for ',
                  c, 'o_O')
            exit()

        # test if it's the ID, in this case convert to integer
        if c=='ID' or c=='id' or c=='IDs' or c=='UNIQUE_ID':
            data_types[c] = 'K'
            temp = np.asarray(all_cols_content[c],dtype=str)
            try:
                all_cols_content[c] = np.asarray(temp,dtype=int)
                sorted_ids = sorted(np.asarray(temp,dtype=int))
                sorted_ids_index = np.asarray([list(np.asarray(temp,dtype=int)).index(ind) for ind in sorted_ids])

            except: # in case there are 'XXX_0' (multiple clumps)
                all_cols_content[c] = np.asarray(temp,dtype=str)
                data_types[c] = '20A'
                # sort IDs if str with 'XXX_0'
                ints = []
                for t in temp:
                    try:
                        ints.append(int(t))
                    except:
                        pass
                sorted_ints = sorted(ints)
                sorted_ints_all = []

                for sints in sorted_ints:
                    here_missing = [m for m in temp if str(sints)+'_' in m 
                                    and str(m)[:-2] in str(sints)]
                    sorted_here_missing = sorted(here_missing)
                    sorted_ints_all += [str(sints)]
                    sorted_ints_all += sorted_here_missing
                sorted_ids_index = np.asarray([list(temp).index(ind)
                                               for ind in sorted_ints_all])

    cols = []
    cols_sorted = sorted(all_cols_content.keys())
    for c in cols_sorted:
        if c=='ID' or c=='UNIQUE_ID': # To put ID first
            array = np.asarray(all_cols_content[c])[sorted_ids_index]
            col = fits.Column(name=c,format=data_types[c],array=array)
            cols.append(col)

    # put RA and DEC next
    for c in cols_sorted:
        if 'RA' in c or 'Ra' in c:
            array = np.asarray(all_cols_content[c])[sorted_ids_index]
            col = fits.Column(name=c,format=data_types[c],array=array)
            cols.append(col)
    for c in cols_sorted:
        if 'DEC' in c or 'Dec' in c:
            array = np.asarray(all_cols_content[c])[sorted_ids_index]
            col = fits.Column(name=c,format=data_types[c],array=array)
            cols.append(col)

    exclude = ['ID','RA','Ra','DEC','Dec']
    # fill with all other columns, but sorted
    for c in cols_sorted:
        test = [i for i in exclude if i in c]
        if len(test)==0 :
            array = np.asarray(all_cols_content[c])[sorted_ids_index]
            col = fits.Column(name=c,format=data_types[c],array=array)
            cols.append(col)


    tbhdu = fits.BinTableHDU.from_columns(cols)

    current_file_name = inspect.getfile(inspect.currentframe()) 
    prihdr = fits.Header()
    prihdr['SCRIPT'] = current_file_name
    prihdr['DATE'] = str(time.strftime("%d/%m/%Y"))
    prihdr['TIME'] = str(time.strftime("%H:%M:%S"))
    prihdu = fits.PrimaryHDU(header=prihdr)
    thdulist = fits.HDUList([prihdu,tbhdu])
    thdulist.writeto(f,overwrite=True)
    print('Wrote file',f)

def invert_dict(d):
    # reverse keys and values
    inv_map = {v: k for k, v in d.items()}
    return inv_map

def reshape_dict_in_dict(old_dict,keyname):
    # make a dictionary of lists from a dictionary of dictionaries
    
    new_vals = list(old_dict) # the old keys
    new_dict = {keyname:new_vals}
    for od in old_dict[new_vals[0]]: # initiate lists
        new_dict[od] = []

    for nv in new_vals:
        for od in old_dict[new_vals[0]]:
            temp = new_dict[od]
            temp.append(old_dict[nv][od])
            new_dict[od] = temp

    return new_dict

def read_image_fits_file(image,hdu):

    # open segmentation map
    hdulist = fits.open(image)
    data = hdulist[hdu]._hdu
    header = hdulist[hdu].header
    hdulist.close()

    return data,header  
