# 12 V PCB cost estimate

Price references checked **12 October 2026**, in **Canadian dollars**. The current Revision C four-port carrier is 50 × 100 mm, two layers, 2 oz copper, ENIG, with 47 fitted parts including four vertical RJ11 jacks, two Nano sockets and the barrel jack. All components are factory soldered. The existing Nano, power supply and LED strip are excluded, as are the enclosure and external cables.

Allow roughly **CAD $225–400 for one fully assembled carrier**, or **CAD $400–650 total for five** (about $80–130 each). These estimates include a shipping allowance to Ontario and exclude tax. They are planning ranges derived from component prices and published assembly fees, **not a manufacturer quote**. This budget carries forward the earlier 110 × 100 mm design's allowances: the smaller Revision C board may reduce fabrication cost, but its parts and assembly scope are unchanged. Prices have not been rechecked for the layout revision. No files have been submitted for quoting and no order has been placed.

| Estimated cost, CAD                       | Description                                                                                                                                                                                 | One assembled board | Five assembled boards |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | --------------------- |
| Bare PCB fabrication lot                  | Manufacturing the empty boards: copper tracks, holes, protective coating and printed labels, with no components installed. Includes any minimum board batch, even if only one is assembled. | $40–80              | $40–80                |
| Components (materials only)               | Buying all fitted parts: resistors, capacitors, chips, MOSFETs, fuses, two Nano sockets, four RJ11 jacks and the barrel jack. Assembly labor is listed separately below.                    | $50–65              | $200–275              |
| Procurement, spare parts and handling     | Sourcing and handling fees, spare components and minimum purchase quantities required by the assembler.                                                                                     | $20–45              | $25–50                |
| Setup, stencil, SMT and through-hole work | Preparing the assembly process and soldering every component. SMT covers surface-mounted parts; through-hole work includes both Nano sockets, all four RJ11 jacks and the barrel jack.      | $90–160             | $100–175              |
| Shipping allowance to Ontario             | Estimated delivery cost for the completed boards; final shipping depends on the supplier and delivery service.                                                                              | $25–50              | $30–60                |
| Calculated total before tax               | Sum of the fabrication, parts, procurement, assembly and shipping ranges above.                                                                                                             | $225–400            | $395–640              |
| Rounded planning budget before tax        | Rounded total to use for planning; this is an estimate, not a supplier quote.                                                                                                               | **$225–400**        | **$400–650**          |

The fabrication allowance includes the small lot of bare boards a supplier may require, even when only one is assembled. Procurement and spare-part charges vary with assembler inventory, minimum purchase quantities and handling. The shipping numbers are allowances, not checkout prices; any separate import duties or courier clearance charges are outside this estimate. The fabrication and assembly line items are estimates for an overseas prototype service, not a local Canadian assembly shop.

Ontario's HST rate is 13%. Applying that rate as a budgeting allowance gives approximately **$255–455 for one**, or **$450–735 for five**, with the final tax and import charges determined at checkout or delivery. [CRA GST/HST rates](https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/gst-hst-businesses/charge-collect-which-rate.html)

## Public prices behind the estimate

The following Canadian distributor prices were visible when checked. They are examples from the actual BOM, before tax and shipping; the assembler's sourcing price can differ.

| Part                                    | Per-board quantity | Small-quantity unit price, CAD |
| --------------------------------------- | ------------------ | ------------------------------ |
| Würth 615004144121 vertical RJ11        | 4                  | $1.42                          |
| Samtec SSQ-115-01-G-S Nano socket       | 2                  | $5.59                          |
| Same Sky PJ-063AH barrel jack           | 1                  | $2.15                          |
| Panasonic EEH-ZL1V471P bulk capacitor   | 1                  | $4.94                          |
| Littelfuse 04513.15MRL branch fuse      | 4                  | $3.61                          |
| TI UCC27524ADR gate driver              | 2                  | $2.13                          |
| AOS AOD4184A MOSFET                     | 3                  | $1.92                          |

Sources: [RJ11](https://www.digikey.ca/fr/products/detail/w%C3%BCrth-elektronik/615004144121/2627288), [Nano sockets](https://www.digikey.ca/en/products/detail/samtec-inc/SSQ-115-01-G-S/1110604), [barrel jack](https://www.mouser.ca/ProductDetail/Same-Sky/PJ-063AH?qs=WyjlAZoYn51bQfA53nMcVA%3D%3D), [capacitor](https://www.digikey.ca/en/products/detail/panasonic-industry/EEH-ZL1V471P/22494086), [branch fuse](https://www.digikey.ca/en/products/detail/littelfuse-inc/04513-15MRL/700825), [gate driver](https://www.mouser.ca/ProductDetail/Texas-Instruments/UCC27524ADR?qs=e5T%2FzGlhGOZ42nP6sM3wCQ%3D%3D), [MOSFET](https://www.digikey.ca/en/products/detail/alpha-omega-semiconductor-inc/AOD4184A/2353886).

These seven lines total approximately $48.41 at the displayed unit prices; the remaining fuses, regulator, protection devices and passives bring the fitted BOM toward the $50–65 allowance. Quantity breaks reduce the five-board component cost. Adding two jacks and two branch fuses costs roughly $10 in small-quantity parts; these connectors are not the main cost of the order.

JLCPCB's published Standard assembly fee table shows approximately US $26 for single-side setup, $8 for a stencil, $1.53 per loaded part type, $16 for two rigid-board fixtures and $3.58 for hand-soldering labor, plus placement/joint charges and the parts themselves. With roughly twenty SMT part types, setup-related charges can be around US $85 before fabrication and shipping. The budget uses a rounded **1 USD = 1.40 CAD planning assumption**, not a guaranteed exchange rate. [JLCPCB assembly fee schedule](https://jlcpcb.com/help/article/pcb-assembly-price)

Revision C fits within 100 × 100 mm, but the 2 oz copper, ENIG finish, components and mixed SMT/through-hole assembly still need to be included in the quote. An advertised bare-board special does not represent the assembled price. [JLCPCB fabrication cost factors](https://jlcpcb.com/blog/custom-pcb-cost)

For a single assembled board, PCBWay publishes a one-piece assembly minimum. JLCPCB currently publishes a two-board assembly minimum, so it cannot be assumed to supply the one-board scenario at these fees. Its fee schedule is used as an assembly-cost reference, not as an offer for this exact BOM. Both the supplier's acceptance of the selected through-hole parts and the final component availability need confirmation in a real quote. [PCBWay minimum](https://www.pcbway.com/helpcenter/pcb_assembly_ordering/What_s_the_min_quantity_of_assembly_.html), [JLCPCB prototype assembly](https://jlcpcb.com/solutions/pcb-prototype-assembly)

Request a quote for **all seven connectors installed**, including both Nano sockets, with the exact BOM and assembly archive. A quote for bare boards or SMT-only population is a different scope. Five boards spread the setup costs but also commit more money before the first prototype is tested.
