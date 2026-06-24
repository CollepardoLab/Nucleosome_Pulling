import numpy as np
import subprocess

def closest(list, Number):
    aux = []
    for val in list:
        aux.append(abs(Number-val))

    return aux.index(min(aux))

def dump_frame_to_data_file(dump_fname, og_data_fname):
    dump_file    = [line.rstrip('\n') for line in open(dump_fname)]
    og_data_file = [line.rstrip('\n') for line in open(og_data_fname)]

    # need to get the positions of the beads, and the quaternions of the ellipsoids
    values=list()
    num_atoms = int(og_data_file[2].split()[0])
    num_ellipsoids = int(og_data_file[3].split()[0])

    print(num_atoms)
    print(num_ellipsoids)

    xx = dump_file[5]
    yy = dump_file[6]
    zz = dump_file[7]


    for i in range(9,num_atoms+9):
        values.append(np.array(dump_file[i].split(),dtype=float))

    # now make the new data file
    # box_size
    
    print('Making new data file')
    og_data_file[13] = xx + " xlo xhi"
    og_data_file[14] = yy + " ylo yhi"
    og_data_file[15] = zz + " zlo zhi"

    # atom coords

    for i in range(19,num_atoms+19):
        line = og_data_file[i].split()
        #print(line)
        j = int(line[0])-1-194
        #print(j)
        new_line = line[:2] + [str(values[j][1]),str(values[j][2]),str(values[j][3])] + line[5:]
        new_line= " ".join(new_line)
        #print(new_line)
        og_data_file[i]=new_line

    print('Atom coords done')
    # ellipsoids
    for i in range(19+num_atoms+3,19+num_atoms+3+num_ellipsoids):
        line = og_data_file[i].split()
        #print(line)
        j = int(line[0])-1-194
        new_line = line[:4] + [str(values[j][4]),str(values[j][5]),str(values[j][6]),str(values[j][7])]
        new_line= " ".join(new_line)
        #print(new_line)
        og_data_file[i]=new_line
    # leave bonds

    return og_data_file


hi=725
lo=25
Nwindows=60
ws=np.linspace(lo,hi,Nwindows)

for I in [1, 2, 3, 4, 5]:

    
    thermofile=open("out_"+str(I)+".txt")


    rows = list()
    for line in thermofile:
        sline=line.split()
        if len(sline) == 7:
            try:
                rows.append(np.array(sline,dtype=float))
            except:
                ValueError

    rows=np.array(rows)

    vex    = rows[:,6]
    tsteps = rows[:,0]

    i=0

    wsteps=list()
    for w in ws:
        a = closest(vex[i:],w)
        i=i+a
        #print(i)
        #print(w)
        #print(vex[i])
        wsteps.append(int(np.round(tsteps[i],-4)))

    print(wsteps)


    num_atoms = int(subprocess.check_output('head -n 10 dna_1.dump | grep -A1 "NUMBER OF ATOMS" | tail -1',shell=True))

    print(num_atoms)
    # then turn them into data files
    i=1
    for a in wsteps:
        print(i)
        dfile = "dna_"+str(I)+".dump"
        lnum = num_atoms + 7
        grep = "grep -w -A " + str(lnum) + " -B 1 " + str(a) + " " + dfile + " > data_start_files_no_LH/temp_"+str(i) + ".dump"
        print(grep)
        subprocess.call(grep,shell=True)
        subprocess.call("cat data_start_files_no_LH/temp_"+str(i)+".dump >> data_start_files_no_LH/traj_"+str(I)+".dump",shell=True)
        dat_file_lines = dump_frame_to_data_file("data_start_files_no_LH/temp_"+str(i)+".dump","nucl_no_LH.txt")
        dfile = open("data_start_files_no_LH/data_file_"+str(I)+"_"+str(i)+".txt","w")
        for line in dat_file_lines:
            dfile.write(line+"\n")
        dfile.close()
        i=i+1






