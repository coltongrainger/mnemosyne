#
# tree_wdgt_wdgt.py <Peter.Bienstman@UGent.be>
#

from PyQt4 import QtCore, QtGui

from mnemosyne.libmnemosyne.translator import _
from mnemosyne.libmnemosyne.component import Component
from mnemosyne.libmnemosyne.criteria.default_criterion import DefaultCriterion

# Code reuse through inheritance.
from mnemosyne.pyqt_ui.tag_tree_widget import TagDelegate, TagTreeWidget


class CardTypeDelegate(TagDelegate):

    def setEditorData(self, editor, index):
        # Get rid of the card count.
        self.old_node_label = \
            index.model().data(index).toString().rsplit(" (", 1)[0]
        editor.setText(self.old_node_label)


class CardTypesTreeWdgt(TagTreeWidget):

    """Displays all the card types in a tree together with check boxes."""

    def __init__(self, component_manager, parent,
            before_using_libmnemosyne_db_hook=None,
            after_using_libmnemosyne_db_hook=None):
        Component.__init__(self, component_manager)
        QtGui.QWidget.__init__(self, parent)
        self.layout = QtGui.QVBoxLayout(self)
        self.tree_wdgt = QtGui.QTreeWidget(self)
        self.tree_wdgt.setHeaderHidden(True)
        self.layout.addWidget(self.tree_wdgt)
        self.delegate = CardTypeDelegate(component_manager, self)
        self.tree_wdgt_wdgt.setItemDelegate(self.delegate)
        self.delegate.rename_node.connect(self.rename_node)
        self.delegate.redraw_node.connect(self.redraw_node)
        # Context menu.
        self.tree_wdgt.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_wdgt.customContextMenuRequested.\
            connect(self.context_menu)

    def context_menu(self, point):
        if not self.tree_wdgt.currentItem() in self.can_be_renamed:
            return
        menu = QtGui.QMenu(self)
        rename_action = QtGui.QAction(_("&Rename"), menu)
        rename_action.triggered.connect(self.menu_rename)
        menu.addAction(rename_action)
        delete_action = QtGui.QAction(_("&Delete"), menu)
        delete_action.setShortcut(QtGui.QKeySequence.Delete)
        delete_action.triggered.connect(self.menu_delete)
        if not self.tree_wdgt.currentItem() in self.can_be_deleted:
            delete_action.setEnabled(False)
        menu.addAction(delete_action)
        menu.exec_(self.tree_wdgt.mapToGlobal(point))

    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            if self.tree_wdgt.currentItem() in self.can_be_renamed:
                self.menu_rename()
        elif event.key() in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
            if self.tree_wdgt.currentItem() in self.can_be_deleted:
                self.menu_delete()

    def menu_rename(self):
        card_type = \
            self.card_type_for_node_item[self.tree_wdgt.currentItem()]

        from mnemosyne.pyqt_ui.ui_rename_card_type_dlg \
            import Ui_RenameCardTypeDlg

        class RenameDlg(QtGui.QDialog, Ui_RenameCardTypeDlg):
            def __init__(self, old_card_type_name):
                QtGui.QDialog.__init__(self)
                self.setupUi(self)
                self.card_type_name.setText(old_card_type_name)

        dlg = RenameDlg(card_type.name)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            self.controller().rename_card_type(card_type,
                unicode(dlg.card_type_name.text()))
            self.rebuild()

    def menu_delete(self):
        card_type = \
            self.card_type_for_node_item[self.tree_wdgt.currentItem()]
        answer = self.main_widget().show_question(_("Delete card type?"),
            _("Yes"), _("No"), "")
        if answer == 1:  # No
            return
        self.controller().delete_card_type(card_type)
        self.rebuild()

    def display(self, criterion=None):
        # Avoid multiple connections.
        try:
            self.tree_wdgt.itemChanged.disconnect(self.tree_item_changed)
        except TypeError:
            pass
        # Create criterion if needed.
        if criterion is None:
            criterion = DefaultCriterion(self.component_manager)
        # Determine number of cards at each level of the tree.
        root_count = 0
        count_for_card_type = {}
        count_for_fact_view = {}
        for card_type in self.card_types():
            card_type_count = 0
            for fact_view in card_type.fact_views:
                count = self.database().card_count_for_fact_view\
                    (fact_view, active_only=False)
                card_type_count += count
                count_for_fact_view[fact_view] = count
            count_for_card_type[card_type] = card_type_count
            root_count += card_type_count
        # Fill widget.
        self.can_be_deleted = []
        self.can_be_renamed = []
        self.tree_wdgt.clear()
        self.card_type_for_node_item = {}
        self.card_type_fact_view_ids_for_node_item = {}
        root_item = QtGui.QTreeWidgetItem(self.tree_wdgt,
            [_("All card types (%d)") % root_count], 0)
        root_item.setFlags(root_item.flags() | \
           QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsTristate)
        root_item.setCheckState(0, QtCore.Qt.Checked)
        for card_type in self.card_types():
            card_type_item = QtGui.QTreeWidgetItem(root_item, ["%s (%d)" % \
                (_(card_type.name), count_for_card_type[card_type])], 0)
            card_type_item.setFlags(card_type_item.flags() | \
                QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsTristate)
            card_type_item.setCheckState(0, QtCore.Qt.Checked)
            if count_for_card_type[card_type] == 0 and \
                self.database().is_user_card_type(card_type):
                    self.can_be_deleted.append(card_type_item)
            if self.database().is_user_card_type(card_type):
                self.can_be_renamed.append(card_type_item)
                card_type_item.setFlags(card_type_item.flags() | \
                    QtCore.Qt.ItemIsEditable)
            self.card_type_for_node_item[card_type_item] = card_type
            for fact_view in card_type.fact_views:
                fact_view_item = QtGui.QTreeWidgetItem(card_type_item,
                    ["%s (%d)" % (_(fact_view.name),
                    count_for_fact_view[fact_view])], 0)
                fact_view_item.setFlags(fact_view_item.flags() | \
                    QtCore.Qt.ItemIsUserCheckable)
                if (card_type.id, fact_view.id) in \
                    criterion.deactivated_card_type_fact_view_ids:
                    check_state = QtCore.Qt.Unchecked
                else:
                    check_state = QtCore.Qt.Checked
                fact_view_item.setCheckState(0, check_state)
                self.card_type_fact_view_ids_for_node_item[fact_view_item] = \
                    (card_type.id, fact_view.id)
        self.tree_wdgt.expandAll()
        self.tree_wdgt.itemChanged.connect(self.tree_item_changed)

    def checked_to_criterion(self, criterion):
        criterion.deactivated_card_type_fact_view_ids = set()
        for item, card_type_fact_view_ids in \
                self.card_type_fact_view_ids_for_node_item.iteritems():
            if item.checkState(0) == QtCore.Qt.Unchecked:
                criterion.deactivated_card_type_fact_view_ids.add(\
                    card_type_fact_view_ids)
        return criterion

    def rebuild(self):

        """To be called when external events invalidate the card type tree,
        e.g. due to edits in the card browser widget.

        """

        saved_criterion = DefaultCriterion(self.component_manager)
        self.checked_to_criterion(saved_criterion)
        # Now we've saved the checked state of the tree.
        # Saving and restoring the selected state is less trivial, because
        # in the case of trees, the model indexes have parents which become
        # invalid when creating the widget.
        # The solution would be to save card types and reselect those in the
        # new widget.
        self.display(saved_criterion)
