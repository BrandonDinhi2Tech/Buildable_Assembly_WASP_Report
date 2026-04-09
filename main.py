import item
import assembly
import location
import report_gen


if __name__ == "__main__":
    location.update_location_table()
    item.entire_inventory_api_call('item_list.csv')
    item.inventory_to_database('item_list.csv')
    assembly.update_bom_table()
    report_gen.create_report('800002')