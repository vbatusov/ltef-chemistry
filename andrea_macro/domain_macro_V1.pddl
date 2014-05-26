;Planning Domain for the MACRO problem
;NON-Recursive definitions of Alkyls

(define (domain Chemical)
(:requirements :derived-predicates :typing :equality)
(:types chlorine bromine iodine - halogenNotFluorineNotAstatine
		fluorine halogenNotFluorineNotAstatine - halogenNotAstatine
		astatine halogenNotAstatine - halogen
		oxygen sulfure - chalcogen
		lithium sodium potassium rubidium caesium - alkali_metal_NotFrancium
		alkali_metal_NotFrancium francium - alkali_metal
		alkali_metal chalcogen halogen nitrogen - atomNotHydrogenNotCarbon
		hydrogen carbon atomNotHydrogenNotCarbon - atom
) 
		
(:predicates 
(bond ?x - atom ?y - atom)
(doublebond ?x - atom ?y - atom)
;DERIVED PREDICATES
(ohIon ?o - oxygen ?h - hydrogen)
(ester ?c - carbon ?o - oxygen)
(water ?h - hydrogen ?o - oxygen)
(strongacid_HX ?h - hydrogen ?x - halogenNotFluorineNotAstatine)
(strongacid_OH_H2SO4 ?h - hydrogen ?o - oxygen)
(strongacid_OH_nitric ?h - hydrogen ?o - oxygen)
(strongacid_OH_HCLO3 ?h - hydrogen ?o - oxygen)
(strongacid_OH_HCLO4 ?h - hydrogen ?o - oxygen)
(alcohol ?o - oxygen ?h - hydrogen)
(strongbase_alkalimetal_oxygen ?x - alkali_metal_NotFrancium ?o - oxygen)
(strongbase_NaH ?h - hydrogen ?na - sodium)
(alkyl ?c - carbon)
(alkyl_1_a ?c - carbon)
(alkyl_1_b ?c - carbon)
(alkyl_2_a ?c - carbon)
(alkyl_2_b ?c - carbon)
(alkyl_3_a ?c - carbon)
(alkyl_3_b ?c - carbon)
(alkyl_3_c ?c - carbon)
(alkyl_3_d ?c - carbon)
(alkyl_4_a ?c - carbon)
(alkyl_4_b ?c - carbon)
(alkyl_4_c ?c - carbon)
(alkyl_4_d ?c - carbon)
(alkyl_4_e ?c - carbon)
(alkyl_4_f ?c - carbon)
(alkyl_4_g ?c - carbon)
(alkyl_4_h ?c - carbon)
(alkyl_halide ?x - halogen ?c - carbon)
(alkoxide_salt ?x - alkali_metal ?o - oxygen)
(ether ?o - oxygen)
(mineral_acid_HX ?h - hydrogen ?x - halogenNotAstatine)
(mineral_acid_HO_nitric ?h - hydrogen ?o - oxygen)
(mineral_acid_HO_H2SO4 ?h - hydrogen ?o - oxygen)
;DERIVED PREDICATES FOR THE MACRO APPROACH
(carboxylic_acid ?o - oxygen ?h - hydrogen)
(carboxylate_salt ?x - alkali_metal ?o - oxygen)
)

;PLANNING ACTIONS

;PLANNING ACTION #1

(:action carboxylicAcid_base_reaction_1
:parameters (?o1 - oxygen ?h1 - hydrogen ?x - alkali_metal_NotFrancium ?o2 - oxygen) 
:precondition (and (not (= ?o1 ?o2)) (carboxylic_acid ?o1 ?h1) (strongbase_alkalimetal_oxygen ?x ?o2))
:effect (and (bond ?o1 ?x) (bond ?x ?o1) (bond ?h1 ?o2) (bond ?o2 ?h1)
	     (not (bond ?h1 ?o1)) (not (bond ?o1 ?h1)) (not (bond ?x ?o2)) (not (bond ?o2 ?x)))
)

(:action carboxylicAcid_base_reaction_2
:parameters (?o1 - oxygen ?h1 - hydrogen ?x - sodium ?h2 - hydrogen) 
:precondition (and (not (= ?h1 ?h2)) (carboxylic_acid ?o1 ?h1) (strongbase_NaH ?h2 ?x))
:effect (and (bond ?o1 ?x) (bond ?x ?o1) (bond ?h1 ?h2) (bond ?h2 ?h1)
	     (not (bond ?h1 ?o1)) (not (bond ?o1 ?h1)) (not (bond ?x ?h2)) (not (bond ?h2 ?x)))
)

;PLANNING ACTION #2

(:action alcohol_base_reaction_1
:parameters (?h1 - hydrogen ?o1 - oxygen  ?o2 - oxygen ?x - alkali_metal_NotFrancium) 
:precondition (and (not (= ?o1 ?o2)) (alcohol ?o1 ?h1) (strongbase_alkalimetal_oxygen ?x ?o2))
:effect (and (bond ?o1 ?x) (bond ?x ?o1) (bond ?h1 ?o2) (bond ?o2 ?h1)
	     (not (bond ?h1 ?o1)) (not (bond ?o1 ?h1)) (not (bond ?x ?o2)) (not (bond ?o2 ?x)))
)

(:action alcohol_base_reaction_2
:parameters (?h1 - hydrogen ?o1 - oxygen ?h2 - hydrogen ?x - sodium) 
:precondition (and (not (= ?h1 ?h2)) (alcohol ?o1 ?h1) (strongbase_NaH ?h2 ?x))
:effect (and (bond ?o1 ?x) (bond ?x ?o1) (bond ?h1 ?h2) (bond ?h2 ?h1)
	     (not (bond ?h1 ?o1)) (not (bond ?o1 ?h1)) (not (bond ?x ?h2)) (not (bond ?h2 ?x)))
)

;PLANNING ACTION #3

(:action ester_water_reaction_1
:parameters (?c1 - carbon ?o1 - oxygen ?h1 - hydrogen ?o2 - oxygen ?h2 - hydrogen ?o3 - oxygen) 
:precondition (and (not (= ?o1 ?o2)) (not (= ?o1 ?o3)) (not (= ?o2 ?o3)) (not (= ?h1 ?h2)) (ester ?c1 ?o1) (water ?h1 ?o2)
		   (or (strongacid_OH_H2SO4 ?h2 ?o3) (strongacid_OH_nitric ?h2 ?o3) (strongacid_OH_HCLO3 ?h2 ?o3) (strongacid_OH_HCLO4 ?h2 ?o3)))
:effect (and (bond ?c1 ?o2) (bond ?o2 ?c1) (bond ?o1 ?h2) (bond ?h2 ?o1) (bond ?o3 ?h1) (bond ?h1 ?o3)
	     (not (bond ?c1 ?o1)) (not (bond ?o1 ?c1)) (not (bond ?h1 ?o2)) (not (bond ?o2 ?h1)) (not (bond ?h2 ?o3)) (not (bond ?o3 ?h2)))
)

(:action ester_water_reaction_2
:parameters (?c1 - carbon ?o1 - oxygen ?h1 - hydrogen ?o2 - oxygen ?h2 - hydrogen ?x4 - halogenNotFluorineNotAstatine) 
:precondition (and (not (= ?o1 ?o2)) (not (= ?h1 ?h2)) (ester ?c1 ?o1) (water ?h1 ?o2) (strongacid_HX ?h2 ?x4))
:effect (and (bond ?c1 ?o2) (bond ?o2 ?c1) (bond ?o1 ?h2) (bond ?h2 ?o1) (bond ?x4 ?h1) (bond ?h1 ?x4)
	     (not (bond ?c1 ?o1)) (not (bond ?o1 ?c1)) (not (bond ?h1 ?o2)) (not (bond ?o2 ?h1)) (not (bond ?h2 ?x4)) (not (bond ?x4 ?h2)))
)

;PLANNING ACTION #4

(:action alkoxideSalt_alkylHalide_reaction
:parameters (?o1 - oxygen ?x1 - alkali_metal ?c1 - carbon  ?y1 - halogen) 
:precondition (and (alkoxide_salt ?x1 ?o1) (alkyl_halide ?y1 ?c1))
:effect (and (bond ?c1 ?o1) (bond ?o1 ?c1) (bond ?x1 ?y1) (bond ?y1 ?x1)
	     (not (bond ?x1 ?o1)) (not (bond ?o1 ?x1)) (not (bond ?c1 ?y1)) (not (bond ?y1 ?c1)))
)

;PLANNING ACTION #5

(:action ether_mineralAcid_reaction_1
:parameters (?o1 - oxygen ?c1 - carbon ?h1 - hydrogen ?o2 - oxygen) 
:precondition (and (not (= ?o1 ?o2)) (ether ?o1) (bond ?c1 ?o1) (or (mineral_acid_HO_nitric ?h1 ?o2) (mineral_acid_HO_H2SO4 ?h1 ?o2)))
:effect (and (bond ?o1 ?h1) (bond ?h1 ?o1) (bond ?c1 ?o2) (bond ?o2 ?c1)
	     (not (bond ?c1 ?o1)) (not (bond ?o1 ?c1)) (not (bond ?h1 ?o2)) (not (bond ?o2 ?h1)))
)

(:action ether_mineralAcid_reaction_2
:parameters (?o1 - oxygen ?c1 - carbon ?h1 - hydrogen ?x1 - halogenNotAstatine) 
:precondition (and (ether ?o1) (bond ?c1 ?o1) (mineral_acid_HX ?h1 ?x1))
:effect (and (bond ?o1 ?h1) (bond ?h1 ?o1) (bond ?c1 ?x1) (bond ?x1 ?c1)
	     (not (bond ?c1 ?o1)) (not (bond ?o1 ?c1)) (not (bond ?h1 ?x1)) (not (bond ?x1 ?h1)))
)


;DERIVED PREDICATES

(:derived (ohIon ?o - oxygen ?h - hydrogen) 
	  (and (bond ?o ?h) (not (exists (?m - atom) (and (not (= ?o ?m)) (not (= ?h ?m)) (bond ?o ?m) (bond ?h ?m))))))

(:derived (ester ?c - carbon ?o - oxygen) 
	  (and (bond ?c ?o) (exists (?o2 - oxygen ?c2 - carbon ?c3 - carbon) 
	  	                    (and (not (= ?o ?o2)) (doublebond ?o2 ?c) (not (= ?c ?c2)) (not (= ?c ?c3)) 
				         (not (= ?c2 ?c3)) (bond ?c ?c2) (bond ?o ?c3) (alkyl ?c2) (alkyl ?c3))))
)

(:derived (water ?h - hydrogen ?o - oxygen) 
	  (and (bond ?o ?h) (exists (?h2 - hydrogen) (and (not (= ?h ?h2)) (bond ?o ?h2))))
)

(:derived (strongacid_HX ?h - hydrogen ?x - halogenNotFluorineNotAstatine) (bond ?h ?x))

(:derived (strongacid_OH_H2SO4 ?h - hydrogen ?o - oxygen) 
	  (and (bond ?o ?h) (exists (?su - sulfure ?o2 - oxygen ?o3 - oxygen ?o4 - oxygen ?h2 - hydrogen) 
				    (and (not (= ?h ?h2)) (not (= ?o ?o2)) (not (= ?o ?o3)) (not (= ?o ?o4)) (not (= ?o2 ?o3)) 
					 (not (= ?o2 ?o4)) (not (= ?o3 ?o4)) (bond ?o ?su) (bond ?o2 ?su) (bond ?o2 ?h2) (doublebond ?o3 ?su) 						 (doublebond ?o4 ?su)))))

(:derived (strongacid_OH_nitric ?h - hydrogen ?o - oxygen) 
	  (and (bond ?o ?h) (exists (?o2 - oxygen ?o3 - oxygen ?n - nitrogen) 
				    (and (not (= ?o ?o2)) (not (= ?o ?o3)) (not (= ?o2 ?o3)) (bond ?o ?n) (bond ?o2 ?n) (doublebond ?o3 ?n)))))

(:derived (strongacid_OH_HCLO3 ?h - hydrogen ?o - oxygen) 
	  (and (bond ?o ?h) (exists (?cl - chlorine ?o2 - oxygen ?o3 - oxygen) 
	                    	    (and (not (= ?o ?o2)) (not (= ?o ?o3)) (not (= ?o2 ?o3)) (bond ?o ?cl) 
				    (doublebond ?o2 ?cl) (doublebond ?o3 ?cl)))))

(:derived (strongacid_OH_HCLO4 ?h - hydrogen ?o - oxygen) 
	  (and (bond ?o ?h) (exists (?cl - chlorine ?o2 - oxygen ?o3 - oxygen ?o4 - oxygen) 
			            (and (not (= ?o ?o2)) (not (= ?o ?o3)) (not (= ?o ?o4)) (not (= ?o2 ?o3)) (not (= ?o2 ?o4)) (not (= ?o3 ?o4)) 					    (bond ?o ?cl) (doublebond ?o2 ?cl) (doublebond ?o3 ?cl) (doublebond ?o4 ?cl)))))
																				
(:derived (alcohol ?o - oxygen ?h - hydrogen) (and (bond ?o ?h) (exists (?c - carbon) (and (bond ?o ?c) (alkyl ?c)))))
														
(:derived (strongbase_alkalimetal_oxygen ?x - alkali_metal_NotFrancium ?o - oxygen) (and (bond ?x ?o) (exists (?h - hydrogen) (bond ?h ?o))))

(:derived (strongbase_NaH ?h - hydrogen ?na - sodium) (bond ?h ?na))	

(:derived (alkyl ?c - carbon) (or (alkyl_1_a ?c) (alkyl_1_b ?c) (alkyl_2_a ?c) (alkyl_2_b ?c) (alkyl_3_a ?c) (alkyl_3_b ?c) (alkyl_3_c ?c) 					   (alkyl_3_d ?c) (alkyl_4_a ?c) (alkyl_4_b ?c) (alkyl_4_c ?c) (alkyl_4_d ?c) (alkyl_4_e ?c) (alkyl_4_f ?c) 					   (alkyl_4_g ?c) (alkyl_4_h ?c)))

(:derived (alkyl_1_a ?c - carbon) 
	  (exists (?h1 - hydrogen) (and (bond ?h1 ?c) 
					(exists (?h2 - hydrogen ?h3 - hydrogen ?x4 - atomNotHydrogenNotCarbon) 
						(and (not (= ?h1 ?h2)) (not (= ?h1 ?h3)) (not (= ?h2 ?h3)) (bond ?h2 ?c) 
						     (bond ?h3 ?c) (bond ?x4 ?c))))))
	
(:derived (alkyl_1_b ?c - carbon) 
	  (exists (?h1 - hydrogen) (and (bond ?h1 ?c) 
					(exists (?h2 - hydrogen ?h3 - hydrogen ?x4 - carbon ?o - oxygen) 
						(and (not (= ?h1 ?h2)) (not (= ?h1 ?h3)) (not (= ?h2 ?h3)) (bond ?h1 ?c) (bond ?h2 ?c) 
						     (bond ?h3 ?c) (not (= ?x4 ?c)) (bond ?x4 ?c) (doublebond ?o ?x4))))))

(:derived (alkyl_2_a ?c - carbon) 
	  (exists (?h1 - hydrogen) (and (bond ?h1 ?c)
					(exists (?h2 - hydrogen ?x4 - atomNotHydrogenNotCarbon ?c2 - carbon ?h3 - hydrogen 
						 ?h4 - hydrogen ?h5 - hydrogen) 
						(and (bond ?x4 ?c) (not (= ?c ?c2)) (bond ?c2 ?c) (not (= ?h1 ?h2)) (bond ?h2 ?c) (not (= ?h1 ?h3)) 							     (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) 
						     (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h4 ?h5)) (bond ?h3 ?c2) (bond ?h4 ?c2) 
						     (bond ?h5 ?c2))))))

(:derived (alkyl_2_b ?c - carbon) 
	  (exists (?h1 - hydrogen) (and (bond ?h1 ?c)
					(exists (?h2 - hydrogen ?x4 - carbon ?c2 - carbon ?h3 - hydrogen 
						 ?h4 - hydrogen ?h5 - hydrogen ?o - oxygen) 
						(and (not (= ?c ?c2)) (not (= ?c ?x4)) (not (= ?c2 ?x4)) (bond ?x4 ?c) (doublebond ?x4 ?o)  
						     (bond ?c2 ?c) (not (= ?h1 ?h2)) (bond ?h2 ?c) (not (= ?h1 ?h3)) 							     (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) 
						     (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h4 ?h5)) (bond ?h3 ?c2) (bond ?h4 ?c2) 
						     (bond ?h5 ?c2))))))

(:derived (alkyl_3_a ?c - carbon)
	  (exists (?h1 - hydrogen ?h2 - hydrogen ?x4 - atomNotHydrogenNotCarbon) 
		  (and (not (= ?h1 ?h2)) (bond ?h1 ?c) (bond ?h2 ?c) (bond ?x4 ?c)
		       (exists (?c2 - carbon ?c3 - carbon ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c2 ?c3)) (bond ?c ?c2) (bond ?c2 ?c3) 
			            (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h2 ?h3)) 
				    (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) 
				    (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h5 ?h6)) 
				    (not (= ?h5 ?h7)) (not (= ?h6 ?h7)) (bond ?c2 ?h3) (bond ?c2 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) 
				    (bond ?c3 ?h7))))))	

(:derived (alkyl_3_b ?c - carbon)
	  (exists (?h1 - hydrogen  ?x4 - atomNotHydrogenNotCarbon) 
		  (and (bond ?h1 ?c) (bond ?x4 ?c)
		       (exists (?c2 - carbon ?c3 - carbon ?h2 - hydrogen ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen)
			       (and (not (= ?h1 ?h2)) (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c2 ?c3)) (bond ?c ?c2) (bond ?c ?c3) 
			            (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h2 ?h3)) 
				    (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) 
				    (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h5 ?h6)) 
				    (not (= ?h5 ?h7)) (not (= ?h6 ?h7)) (bond ?c2 ?h2) (bond ?c2 ?h3) (bond ?c2 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) 
				    (bond ?c3 ?h7))))))	

(:derived (alkyl_3_c ?c - carbon)
	  (exists (?h1 - hydrogen ?h2 - hydrogen ?x4 - carbon ?o - oxygen) 
		  (and (not (= ?h1 ?h2)) (not (= ?x4 ?c)) (bond ?h1 ?c) (bond ?h2 ?c) (bond ?x4 ?c) (doublebond ?x4 ?o)
		       (exists (?c2 - carbon ?c3 - carbon ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c2 ?c3)) (not (= ?c2 ?x4)) (not (= ?c3 ?x4)) 
				    (bond ?c ?c2) (bond ?c2 ?c3) (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) 
				    (not (= ?h1 ?h7)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) 
				    (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) 
				    (not (= ?h4 ?h7)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) (not (= ?h6 ?h7)) (bond ?c2 ?h3) (bond ?c2 ?h4) 
				    (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c3 ?h7))))))	

(:derived (alkyl_3_d ?c - carbon)
	  (exists (?h1 - hydrogen  ?x4 - carbon ?o - oxygen) 
		  (and (not (= ?x4 ?c)) (bond ?h1 ?c) (bond ?x4 ?c) (doublebond ?x4 ?o)
		       (exists (?c2 - carbon ?c3 - carbon ?h2 - hydrogen ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen)
			       (and (not (= ?h1 ?h2)) (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c2 ?c3)) (not (= ?c2 ?x4)) (not (= ?c3 ?x4)) 
			            (bond ?c ?c2) (bond ?c ?c3) (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) 
				    (not (= ?h1 ?h7)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) 
				    (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6))
				    (not (= ?h4 ?h7)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) (not (= ?h6 ?h7)) (bond ?c2 ?h2) (bond ?c2 ?h3) 
				    (bond ?c2 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c3 ?h7))))))

(:derived (alkyl_4_a ?c - carbon)
	  (exists (?h1 - hydrogen ?h2 - hydrogen ?x4 - atomNotHydrogenNotCarbon) 
		  (and (not (= ?h1 ?h2)) (bond ?h1 ?c) (bond ?h2 ?c) (bond ?x4 ?c)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen 
				?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c3 ?c4)) 
				    (bond ?c ?c2) (bond ?c2 ?c3) (bond ?c3 ?c4) (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) 
				    (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h1 ?h8)) (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) 
				    (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) (not (= ?h3 ?h4)) 
				    (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) (not (= ?h4 ?h5)) 
				    (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h4 ?h8)) (not (= ?h4 ?h9)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) 
				    (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) (not (= ?h6 ?h7)) (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) (not (= ?h7 ?h8)) 
				    (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) (bond ?c2 ?h3) (bond ?c2 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) 
				    (bond ?c4 ?h7) (bond ?c4 ?h8) (bond ?c4 ?h9))))))	

(:derived (alkyl_4_b ?c - carbon)
	  (exists (?h1 - hydrogen ?h2 - hydrogen ?x4 - atomNotHydrogenNotCarbon) 
		  (and (not (= ?h1 ?h2)) (bond ?h1 ?c) (bond ?h2 ?c) (bond ?x4 ?c)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen 
				?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c3 ?c4)) 
				    (bond ?c ?c2) (bond ?c2 ?c3) (bond ?c2 ?c4) (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) 
				    (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h1 ?h8)) (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) 
				    (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) (not (= ?h3 ?h4)) 
				    (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) (not (= ?h4 ?h5)) 
				    (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h4 ?h8)) (not (= ?h4 ?h9)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) 
				    (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) (not (= ?h6 ?h7)) (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) (not (= ?h7 ?h8)) 
				    (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) (bond ?c2 ?h3) (bond ?c3 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) 
				    (bond ?c4 ?h7) (bond ?c4 ?h8) (bond ?c4 ?h9))))))	

(:derived (alkyl_4_c ?c - carbon)
	  (exists (?h1 - hydrogen  ?x4 - atomNotHydrogenNotCarbon) 
		  (and (bond ?h1 ?c) (bond ?x4 ?c)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h2 - hydrogen ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen 
			        ?h7 - hydrogen ?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c3 ?c4)) 
				    (bond ?c ?c2) (bond ?c ?c3) (bond ?c3 ?c4) (not (= ?h1 ?h2)) (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) 
				    (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h1 ?h8)) (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) 
				    (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) 
				    (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) 
				    (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h4 ?h8)) (not (= ?h4 ?h9)) (not (= ?h5 ?h6))
				    (not (= ?h5 ?h7)) (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) (not (= ?h6 ?h7)) (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) 
				    (not (= ?h7 ?h8)) (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) (bond ?c2 ?h2) (bond ?c2 ?h3) (bond ?c2 ?h4) 
				    (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c4 ?h7) (bond ?c4 ?h8) (bond ?c4 ?h9))))))

(:derived (alkyl_4_d ?c - carbon)
	  (exists (?x4 - atomNotHydrogenNotCarbon) 
		  (and (bond ?x4 ?c)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h1 - hydrogen ?h2 - hydrogen ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen 
			        ?h6 - hydrogen ?h7 - hydrogen ?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c3 ?c4)) 
				    (bond ?c ?c2) (bond ?c ?c3) (bond ?c ?c4) (not (= ?h1 ?h2)) (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) 
				    (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h1 ?h8)) (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) 
				    (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) 
				    (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) 
				    (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h4 ?h8)) (not (= ?h4 ?h9)) (not (= ?h5 ?h6))
				    (not (= ?h5 ?h7)) (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) (not (= ?h6 ?h7)) (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) 
				    (not (= ?h7 ?h8)) (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) (bond ?c2 ?h2) (bond ?c2 ?h3) (bond ?c2 ?h1) 
				    (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c3 ?h4) (bond ?c4 ?h7) (bond ?c4 ?h8) (bond ?c4 ?h9))))))

(:derived (alkyl_4_e ?c - carbon)
	  (exists (?h1 - hydrogen ?h2 - hydrogen ?x4 - carbon ?o - oxygen) 
		  (and (not (= ?h1 ?h2)) (not (= ?x4 ?c)) (bond ?h1 ?c) (bond ?h2 ?c) (bond ?x4 ?c) (doublebond ?x4 ?o)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen 
				?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c2 ?x4)) 
				    (not (= ?c3 ?c4)) (not (= ?c3 ?x4)) (not (= ?c4 ?x4)) (bond ?c ?c2) (bond ?c2 ?c3) (bond ?c3 ?c4) 
				    (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h1 ?h8)) 
				    (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) 
				    (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) 
				    (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h4 ?h8)) 
				    (not (= ?h4 ?h9)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) (not (= ?h6 ?h7)) 
				    (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) (not (= ?h7 ?h8)) (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) (bond ?c2 ?h3) 
				    (bond ?c2 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c4 ?h7) (bond ?c4 ?h8) (bond ?c4 ?h9))))))

(:derived (alkyl_4_f ?c - carbon)
	  (exists (?h1 - hydrogen ?h2 - hydrogen ?x4 - carbon ?o - oxygen) 
		  (and (not (= ?h1 ?h2)) (not (= ?x4 ?c)) (bond ?h1 ?c) (bond ?h2 ?c) (bond ?x4 ?c) (doublebond ?x4 ?o)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen ?h7 - hydrogen 
				?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c2 ?x4)) 
				    (not (= ?c3 ?c4)) (not (= ?c3 ?x4)) (not (= ?c4 ?x4)) (bond ?c ?c2) (bond ?c2 ?c3) (bond ?c2 ?c4) 
				    (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h1 ?h8)) 
				    (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) 
				    (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) 
				    (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h4 ?h8)) 
				    (not (= ?h4 ?h9)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) (not (= ?h6 ?h7)) 
				    (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) (not (= ?h7 ?h8)) (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) (bond ?c2 ?h3) 
				    (bond ?c3 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c4 ?h7) (bond ?c4 ?h8) (bond ?c4 ?h9))))))	

(:derived (alkyl_4_g ?c - carbon)
	  (exists (?h1 - hydrogen  ?x4 - carbon ?o - oxygen) 
		  (and (not (= ?x4 ?c)) (bond ?h1 ?c) (bond ?x4 ?c) (doublebond ?x4 ?o)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h2 - hydrogen ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen ?h6 - hydrogen 
			        ?h7 - hydrogen ?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c2 ?x4)) 
				    (not (= ?c3 ?c4)) (not (= ?c3 ?x4)) (not (= ?c4 ?x4)) (bond ?c ?c2) (bond ?c ?c3) (bond ?c3 ?c4) 
				    (not (= ?h1 ?h2)) (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) 
				    (not (= ?h1 ?h8)) (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) 
				    (not (= ?h2 ?h7)) (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) 
				    (not (= ?h3 ?h7)) (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) 
				    (not (= ?h4 ?h8)) (not (= ?h4 ?h9)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) 
				    (not (= ?h6 ?h7)) (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) (not (= ?h7 ?h8)) (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) 				    (bond ?c2 ?h2) (bond ?c2 ?h3) (bond ?c2 ?h4) (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c4 ?h7) (bond ?c4 ?h8) 
				    (bond ?c4 ?h9))))))

(:derived (alkyl_4_h ?c - carbon)
	  (exists (?x4 - carbon ?o - oxygen) 
		  (and (not (= ?x4 ?c)) (bond ?x4 ?c) (doublebond ?x4 ?o)
		       (exists (?c2 - carbon ?c3 - carbon ?c4 - carbon ?h1 - hydrogen ?h2 - hydrogen ?h3 - hydrogen ?h4 - hydrogen ?h5 - hydrogen 
			        ?h6 - hydrogen ?h7 - hydrogen ?h8 - hydrogen ?h9 - hydrogen)
			       (and (not (= ?c ?c2)) (not (= ?c ?c3)) (not (= ?c ?c4)) (not (= ?c2 ?c3)) (not (= ?c2 ?c4)) (not (= ?c2 ?x4)) 
				    (not (= ?c3 ?c4)) (not (= ?c3 ?x4)) (not (= ?c4 ?x4)) (bond ?c ?c2) (bond ?c ?c3) (bond ?c ?c4) (not (= ?h1 ?h2)) 					    (not (= ?h1 ?h3)) (not (= ?h1 ?h4)) (not (= ?h1 ?h5)) (not (= ?h1 ?h6)) (not (= ?h1 ?h7)) (not (= ?h1 ?h8)) 
				    (not (= ?h1 ?h9)) (not (= ?h2 ?h3)) (not (= ?h2 ?h4)) (not (= ?h2 ?h5)) (not (= ?h2 ?h6)) (not (= ?h2 ?h7)) 
				    (not (= ?h2 ?h8)) (not (= ?h2 ?h9)) (not (= ?h3 ?h4)) (not (= ?h3 ?h5)) (not (= ?h3 ?h6)) (not (= ?h3 ?h7)) 
				    (not (= ?h3 ?h8)) (not (= ?h3 ?h9)) (not (= ?h4 ?h5)) (not (= ?h4 ?h6)) (not (= ?h4 ?h7)) (not (= ?h4 ?h8)) 
				    (not (= ?h4 ?h9)) (not (= ?h5 ?h6)) (not (= ?h5 ?h7)) (not (= ?h5 ?h8)) (not (= ?h5 ?h9)) (not (= ?h6 ?h7)) 
				    (not (= ?h6 ?h8)) (not (= ?h6 ?h9)) (not (= ?h7 ?h8)) (not (= ?h7 ?h9)) (not (= ?h8 ?h9)) (bond ?c2 ?h2) 
				    (bond ?c2 ?h3) (bond ?c2 ?h1) (bond ?c3 ?h5) (bond ?c3 ?h6) (bond ?c3 ?h4) (bond ?c4 ?h7) (bond ?c4 ?h8) 
				    (bond ?c4 ?h9))))))
																				  
(:derived (alkyl_halide ?x - halogen ?c - carbon) 
	  (and (bond ?c ?x) (alkyl ?c)))

(:derived (alkoxide_salt ?x - alkali_metal ?o - oxygen)	
	  (and (bond ?x ?o) (exists (?c - carbon) (and (bond ?o ?c) (alkyl ?c)))))

(:derived (ether ?o - oxygen) 
	  (exists (?c1 - carbon) (and (bond ?o ?c1) (exists (?c2 - carbon) (and (not (= ?c1 ?c2)) (bond ?o ?c2) (alkyl ?c1) (alkyl ?c2))))))

(:derived (mineral_acid_HX ?h - hydrogen ?x - halogenNotAstatine) (bond ?h ?x))

(:derived (mineral_acid_HO_nitric ?h - hydrogen ?o - oxygen) 
	  (and (bond ?h ?o) (exists (?n - nitrogen ?o2 - oxygen ?o3 - oxygen)
				    (and (not (= ?o ?o2)) (not (= ?o ?o3)) (not (= ?o2 ?o3)) (bond ?o ?n) (bond ?o2 ?n) (doublebond ?o3 ?n)))))

(:derived (mineral_acid_HO_H2SO4 ?h - hydrogen ?o - oxygen) 
	  (and (bond ?h ?o) (exists (?su - sulfure) (and (bond ?o ?su) 
							(exists (?h2 - hydrogen ?o2 - oxygen ?o3 - oxygen ?o4 - oxygen) 
								(and (not (= ?h ?h2)) (not (= ?o ?o2)) (not (= ?o ?o3)) (not (= ?o ?o4)) 
								     (not (= ?o2 ?o3)) (not (= ?o2 ?o4)) (not (= ?o3 ?o4)) (bond ?o2 ?su) 
								     (bond ?o2 ?h2) (doublebond ?o3 ?su) (doublebond ?o4 ?su)))))))

(:derived (carboxylic_acid ?o - oxygen ?h - hydrogen) (and (bond ?h ?o) 
							   (exists (?c1 - carbon ?c2 - carbon ?o2 - oxygen) 
								   (and (not (= ?c1 ?c2)) (not (= ?o ?o2)) (bond ?c1 ?o) (doublebond ?c1 ?o2) 
									(bond ?c1 ?c2) (alkyl ?c2)))))

(:derived (carboxylate_salt ?x - alkali_metal ?o - oxygen) (and (bond ?x ?o) 
							        (exists (?c1 - carbon ?c2 - carbon ?o2 - oxygen) 
								 	(and (not (= ?c1 ?c2)) (not (= ?o ?o2)) (bond ?c1 ?o) (doublebond ?c1 ?o2)
									(bond ?c1 ?c2) (alkyl ?c2)))))

)

